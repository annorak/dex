"""Check core purity and process vocabulary within supported source forms."""

import argparse
import ast
import re
import sys
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ALLOWED_MEMBERS: dict[str, set[str]] = {
    "__future__": {"annotations"},
    "ast": set(
        "parse literal_eval dump walk iter_fields iter_child_nodes "
        "get_docstring get_source_segment copy_location fix_missing_locations "
        "increment_lineno NodeVisitor NodeTransformer".split()
    ),
    "collections": {"abc"},
    "collections.abc": set(
        "Awaitable Coroutine AsyncIterable AsyncIterator AsyncGenerator "
        "Hashable Iterable Iterator Generator Reversible Sized Container "
        "Collection Callable Set MutableSet Mapping MutableMapping "
        "MappingView KeysView ItemsView ValuesView Sequence MutableSequence "
        "ByteString Buffer".split()
    ),
    "dataclasses": set(
        "dataclass field fields replace asdict astuple is_dataclass "
        "InitVar KW_ONLY MISSING FrozenInstanceError".split()
    ),
    "datetime": set(
        "date datetime time timedelta timezone tzinfo UTC MINYEAR MAXYEAR".split()
    ),
    "enum": set(
        "Enum IntEnum StrEnum Flag IntFlag auto unique verify "
        "EnumCheck FlagBoundary ReprEnum property member nonmember".split()
    ),
    "hashlib": {"sha256"},
    "types": {"MappingProxyType"},
    "json": {"dumps", "loads", "JSONDecoder", "JSONEncoder", "JSONDecodeError"},
    "typing": set(
        "Any Annotated Callable ClassVar Concatenate Final Generic Literal "
        "LiteralString NamedTuple Never NewType NoReturn NotRequired Optional "
        "ParamSpec Protocol Required Self TYPE_CHECKING TypeAlias TypeGuard "
        "TypeIs TypeVar TypeVarTuple TypedDict Union Unpack assert_never "
        "assert_type cast final get_args get_origin overload override "
        "runtime_checkable".split()
    ),
}
ALLOWED_MEMBERS["ast"].update(
    name
    for name, value in vars(ast).items()
    if isinstance(value, type) and issubclass(value, ast.AST)
)

FORBIDDEN_NAMES: dict[str, str] = {
    **dict.fromkeys(
        "open input print exit quit credits copyright license".split(), "CORE_IO"
    ),
    **dict.fromkeys(("hash", "id"), "CORE_RANDOM"),
    **dict.fromkeys(
        "__import__ eval exec compile getattr setattr delattr hasattr "
        "globals locals vars dir breakpoint help".split(),
        "CORE_DYNAMIC",
    ),
}
FORBIDDEN_ATTRIBUTES: dict[str, str] = {
    **dict.fromkeys(
        "read readline readlines write writelines flush fileno "
        "read_text read_bytes write_text write_bytes "
        "send sendall recv connect accept listen".split(),
        "CORE_IO",
    ),
    **dict.fromkeys(
        "today now utcnow fromtimestamp utcfromtimestamp timestamp "
        "astimezone strftime strptime".split(),
        "CORE_CLOCK",
    ),
    **dict.fromkeys(
        ("get_type_hints", "evaluate_forward_ref", "ForwardRef"), "CORE_DYNAMIC"
    ),
}
FORBIDDEN_MODULES: dict[str, str] = {
    **dict.fromkeys(
        "os io pathlib socket subprocess shutil tempfile logging "
        "urllib http ftplib smtplib multiprocessing threading asyncio".split(),
        "CORE_IO",
    ),
    **dict.fromkeys(("time",), "CORE_CLOCK"),
    **dict.fromkeys(("random", "secrets", "uuid"), "CORE_RANDOM"),
    **dict.fromkeys(
        ("builtins", "importlib", "inspect", "ctypes", "sys"), "CORE_DYNAMIC"
    ),
}
PROCESS_TERMS = frozenset(
    "invoice invoices vendor vendors community communities hoa ap payable "
    "payables payment payments insurance certificate certificates board signer "
    "signers snow remittance onboarding payroll benefit benefits roster rosters "
    "cutover bramblewick fennor veldren harthmere ashmere rillhaven avenreed "
    "morrowfen asterfen".split()
)
PROCESS_IDS = re.compile(
    r"(?<![a-z0-9])"
    r"(?:c[12](?=$|[^a-z0-9])|w1[-_][pead]\d|onb(?=$|[^a-z0-9])"
    r"|[hs]\d{3}(?=$|[^a-z0-9]))",
    re.IGNORECASE,
)


@dataclass(frozen=True, order=True)
class Violation:
    path: Path
    line: int
    rule: str
    message: str


def find_process_terms(text: str) -> set[str]:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    terms: set[str] = {"process identifier"} if PROCESS_IDS.search(text) else set()
    tokens = set(re.findall(r"[a-z]+", text.casefold()))
    return terms | (tokens & PROCESS_TERMS)


def get_module_name(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    if isinstance(node, ast.Attribute):
        parent = get_module_name(node.value, aliases)
        return f"{parent}.{node.attr}" if parent is not None else None
    return None


def check_source(path: Path, source: str) -> tuple[Violation, ...]:
    tree = ast.parse(source, filename=str(path))
    nodes = list(ast.walk(tree))
    parents = {child: node for node in nodes for child in ast.iter_child_nodes(node)}
    aliases: dict[str, str] = {}
    violations: set[Violation] = set()

    def report(line: int, rule: str, message: str) -> None:
        violations.add(Violation(path, line, rule, message))

    def bind_module(name: str, module: str, line: int) -> None:
        if name in aliases and aliases[name] != module:
            report(line, "CORE_DYNAMIC", "module alias has conflicting imports")
        aliases[name] = module

    def check_import(module: str, member: str | None, line: int) -> None:
        rule = FORBIDDEN_MODULES.get(module.partition(".")[0])
        if rule is not None:
            report(line, rule, "forbidden module import")
        elif member == "*" or (member is not None and member.startswith("__")):
            report(line, "CORE_DYNAMIC", "wildcard and dunder imports are forbidden")
        elif module == "dex.core" or module.startswith("dex.core."):
            return
        elif module not in ALLOWED_MEMBERS:
            report(line, "CORE_IMPORT", "module is not approved for core")
        elif member is not None and member not in ALLOWED_MEMBERS[module]:
            report(line, "CORE_IMPORT", "module member is not approved for core")

    for node in (item for item in nodes if isinstance(item, ast.Import)):
        for entry in node.names:
            check_import(entry.name, None, node.lineno)
            if entry.name in ALLOWED_MEMBERS:
                name = entry.asname or entry.name.partition(".")[0]
                module = entry.name if entry.asname else name
                bind_module(name, module, node.lineno)

    for node in (item for item in nodes if isinstance(item, ast.ImportFrom)):
        if node.level:
            if any(
                entry.name == "*" or entry.name.startswith("__") for entry in node.names
            ):
                report(
                    node.lineno,
                    "CORE_DYNAMIC",
                    "wildcard and dunder imports are forbidden",
                )
            continue
        assert node.module is not None
        for entry in node.names:
            check_import(node.module, entry.name, node.lineno)
            imported = f"{node.module}.{entry.name}"
            if imported in ALLOWED_MEMBERS:
                bind_module(entry.asname or entry.name, imported, node.lineno)

    for node in nodes:
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id.startswith("__"):
                report(node.lineno, "CORE_DYNAMIC", "dunder name access is forbidden")
            rule = FORBIDDEN_NAMES.get(node.id)
            if rule is not None:
                report(node.lineno, rule, "forbidden builtin reference")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                report(
                    node.lineno, "CORE_DYNAMIC", "dunder attribute access is forbidden"
                )
            rule = FORBIDDEN_ATTRIBUTES.get(node.attr)
            if rule is not None:
                report(node.lineno, rule, "forbidden member reference")
            module = get_module_name(node.value, aliases)
            if (
                module is not None
                and module in ALLOWED_MEMBERS
                and node.attr not in ALLOWED_MEMBERS[module]
            ):
                report(
                    node.lineno, "CORE_IMPORT", "module member is not approved for core"
                )
        if isinstance(node, (ast.Name, ast.Attribute)):
            module = get_module_name(node, aliases)
            parent = parents.get(node)
            if module in ALLOWED_MEMBERS and not (
                isinstance(parent, ast.Attribute) and parent.value is node
            ):
                report(
                    node.lineno,
                    "CORE_DYNAMIC",
                    "stdlib modules must be direct attribute receivers",
                )
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for term in find_process_terms(node.value):
                report(node.lineno, "CORE_VOCABULARY", term)

    for line, text in enumerate(source.splitlines(), start=1):
        for term in find_process_terms(text):
            report(line, "CORE_VOCABULARY", term)
    for term in find_process_terms(path.as_posix()):
        report(1, "CORE_VOCABULARY", term)
    return tuple(sorted(violations))


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path)
    args = parser.parse_args(argv)
    root: Path = args.root or Path(__file__).resolve().parents[1] / "src/dex/core"
    if args.root is None and not root.exists():
        print("CORE_SKIP: dex.core has no source files yet")
        return 0
    if not root.is_file() and not root.is_dir():
        print(f"{root}:1: CORE_INPUT: input path does not exist")
        return 2
    if root.is_file() and root.suffix != ".py":
        print(f"{root}:1: CORE_INPUT: expected a Python source file")
        return 2
    paths = [root] if root.is_file() else sorted(root.rglob("*.py"))
    if not paths:
        print(f"{root}:1: CORE_INPUT: no Python source files found")
        return 2
    base = root.parent if root.is_file() else root
    violations: list[Violation] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
            violations.extend(check_source(path.relative_to(base), source))
        except SyntaxError as error:
            print(f"{path}:{error.lineno or 1}: CORE_PARSE: invalid Python syntax")
            return 2
        except (OSError, UnicodeError, ValueError):
            print(f"{path}:1: CORE_INPUT: source could not be read or parsed")
            return 2
    for violation in violations:
        print(
            f"{base / violation.path}:{violation.line}: "
            f"{violation.rule}: {violation.message}"
        )
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
