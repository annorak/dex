import sys
from dataclasses import dataclass
from typing import cast

from grimp import ImportGraph
from importlinter import Contract, ContractCheck, output


@dataclass(frozen=True)
class Violation:
    rule: str
    chain: tuple[str, ...]


def _is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


class DexIsolationContract(Contract):
    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        modules = graph.modules
        dex = {module for module in modules if _is_within(module, "dex")}
        core = {module for module in dex if _is_within(module, "dex.core")}
        demo = {module for module in dex if _is_within(module, "dex.demo")}
        evaluator = {module for module in dex if _is_within(module, "dex.eval")}
        protected = dex - demo - evaluator - {"dex.cli"}
        restricted = demo | evaluator
        forbidden_core = {
            module
            for module in modules - core
            if module.partition(".")[0] not in sys.stdlib_module_names
        }
        violations: list[Violation] = []

        for source in sorted(protected):
            for target in sorted(restricted):
                chain = graph.find_shortest_chain(source, target)
                if chain is not None:
                    violations.append(Violation("DEX-IMPORT-ISOLATION", chain))

        for source in sorted(core):
            for target in sorted(forbidden_core):
                chain = graph.find_shortest_chain(source, target)
                if chain is not None:
                    violations.append(Violation("DEX-CORE-IMPORT", chain))

        for source in sorted(demo):
            for target in sorted(graph.find_modules_directly_imported_by(source)):
                if _is_within(target, "dex.cli"):
                    violations.append(Violation("DEX-DEMO-CLI", (source, target)))
                elif source != "dex.demo.fixtures" and target in evaluator:
                    violations.append(Violation("DEX-FIXTURE-IMPORT", (source, target)))

        return ContractCheck(
            kept=not violations,
            metadata={"violations": tuple(violations)},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        violations = cast(tuple[Violation, ...], check.metadata["violations"])
        for violation in violations:
            output.print_error(
                f"{violation.rule}: {' -> '.join(violation.chain)}",
                bold=False,
            )
