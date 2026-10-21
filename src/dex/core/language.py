import ast
from dataclasses import astuple, dataclass
from datetime import date, timedelta
from typing import cast

from dex.core import program as p


@dataclass(frozen=True)
class Limits:
    source_bytes: int = 65536
    nesting: int = 32
    string_bytes: int = 65536
    collection_count: int = 10000
    integer_magnitude: int = 9223372036854775807
    allocations: int = 16000000
    work: int = 5000000
    functions: int = 128
    ast_nodes: int = 20000
    call_depth: int = 16


DEFAULT_LIMITS = Limits()


@dataclass(frozen=True)
class Usage:
    work: int
    allocations: int


@dataclass(frozen=True)
class LanguageFailure:
    code: str
    path: str
    message: str
    usage: Usage


@dataclass(frozen=True)
class FunctionResult:
    value: p.Value
    usage: Usage


class _Rejected(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message


class _Budget:
    def __init__(self, limits: Limits) -> None:
        self.limits = limits
        self.work = 0
        self.allocations = 0

    def charge(self, work: int = 1, allocations: int = 0) -> None:
        if work > self.limits.work - self.work:
            raise _Rejected("work_limit", "Work budget exhausted.")
        if allocations > self.limits.allocations - self.allocations:
            raise _Rejected("allocation_limit", "Allocation budget exhausted.")
        self.work += work
        self.allocations += allocations

    def usage(self) -> Usage:
        return Usage(self.work, self.allocations)

    def text(self, value: str) -> None:
        if len(value) > self.limits.string_bytes:
            raise _Rejected("string_limit", "Text exceeds byte limit.")
        self.charge(len(value) + 1, len(value) * 4)
        if len(value.encode("utf-8")) > self.limits.string_bytes:
            raise _Rejected("string_limit", "Text exceeds byte limit.")

    def integer(self, value: int) -> None:
        if (
            value > self.limits.integer_magnitude
            or value < -self.limits.integer_magnitude
        ):
            raise _Rejected("integer_limit", "Integer exceeds magnitude limit.")


def _limits(limits: Limits) -> None:
    supplied = cast(tuple[int, ...], astuple(limits))
    defaults = cast(tuple[int, ...], astuple(DEFAULT_LIMITS))
    if any(
        type(value) is not int or value < 1 or value > cap
        for value, cap in zip(supplied, defaults, strict=True)
    ):
        raise _Rejected(
            "invalid_limits",
            "Limits must be positive and no greater than language defaults.",
        )


@dataclass(frozen=True)
class Constant:
    value: p.Value
    schema: p.Schema


@dataclass(frozen=True)
class Variable:
    name: str
    schema: p.Schema


@dataclass(frozen=True)
class Operation:
    operator: str
    arguments: tuple["Expression", ...]
    schema: p.Schema


@dataclass(frozen=True)
class Call:
    function: str
    arguments: tuple["Expression", ...]
    schema: p.Schema


@dataclass(frozen=True)
class FieldAccess:
    record: "Expression"
    name: str
    schema: p.Schema


@dataclass(frozen=True)
class RecordConstructor:
    schema: p.RecordSchema
    arguments: tuple["Expression", ...]


type Expression = (
    Constant | Variable | Operation | Call | FieldAccess | RecordConstructor
)


@dataclass(frozen=True)
class Assign:
    name: str
    value: Expression


@dataclass(frozen=True)
class Return:
    value: Expression


@dataclass(frozen=True)
class If:
    condition: Expression
    when_true: tuple["Statement", ...]
    when_false: tuple["Statement", ...]


@dataclass(frozen=True)
class For:
    name: str
    collection: Expression
    body: tuple["Statement", ...]


type Statement = Assign | Return | If | For


@dataclass(frozen=True)
class CheckedFunction:
    declaration: p.FunctionDeclaration
    instructions: tuple[Statement, ...]


@dataclass(frozen=True)
class CheckedFunctions:
    functions: tuple[CheckedFunction, ...]
    schemas: tuple[p.RecordSchema, ...]
    limits: Limits
    test_results: tuple[FunctionResult, ...]


@dataclass(frozen=True)
class Builtin:
    name: str
    inputs: tuple[p.Schema, ...]
    output: p.Schema


OPERATORS: dict[type[ast.AST], str] = {
    ast.Add: "Add",
    ast.Sub: "Sub",
    ast.Mult: "Mult",
    ast.FloorDiv: "FloorDiv",
    ast.Mod: "Mod",
    ast.USub: "USub",
    ast.UAdd: "UAdd",
    ast.Not: "Not",
    ast.Eq: "Eq",
    ast.NotEq: "NotEq",
    ast.Lt: "Lt",
    ast.LtE: "LtE",
    ast.Gt: "Gt",
    ast.GtE: "GtE",
    ast.And: "And",
    ast.Or: "Or",
}


BUILTINS = (
    Builtin("money", (p.Scalar.INTEGER,), p.Scalar.MONEY),
    Builtin("cents", (p.Scalar.MONEY,), p.Scalar.INTEGER),
    Builtin("parse_money", (p.Scalar.TEXT,), p.Scalar.MONEY),
    Builtin("parse_iso_date", (p.Scalar.TEXT,), p.Scalar.DATE),
    Builtin("parse_us_date", (p.Scalar.TEXT,), p.Scalar.DATE),
    Builtin("add_days", (p.Scalar.DATE, p.Scalar.INTEGER), p.Scalar.DATE),
    Builtin("days_between", (p.Scalar.DATE, p.Scalar.DATE), p.Scalar.INTEGER),
    Builtin("year", (p.Scalar.DATE,), p.Scalar.INTEGER),
    Builtin("month", (p.Scalar.DATE,), p.Scalar.INTEGER),
    Builtin("day", (p.Scalar.DATE,), p.Scalar.INTEGER),
    Builtin(
        "date", (p.Scalar.INTEGER, p.Scalar.INTEGER, p.Scalar.INTEGER), p.Scalar.DATE
    ),
    Builtin("starts_with", (p.Scalar.TEXT, p.Scalar.TEXT), p.Scalar.BOOLEAN),
    Builtin("contains", (p.Scalar.TEXT, p.Scalar.TEXT), p.Scalar.BOOLEAN),
    Builtin("trim", (p.Scalar.TEXT,), p.Scalar.TEXT),
    Builtin("between", (p.Scalar.TEXT, p.Scalar.TEXT, p.Scalar.TEXT), p.Scalar.TEXT),
    Builtin("format_money", (p.Scalar.MONEY,), p.Scalar.TEXT),
    Builtin("format_date", (p.Scalar.DATE,), p.Scalar.TEXT),
)


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise _Rejected(code, message)


def _value(value: p.Value, schema: p.Schema, budget: _Budget, depth: int = 0) -> None:
    _require(
        depth <= budget.limits.nesting, "nesting_limit", "Value nesting exceeds limit."
    )
    budget.charge(1, 32)
    valid = False
    if isinstance(value, p.BoolValue):
        valid = schema == p.Scalar.BOOLEAN and type(value.value) is bool
    elif isinstance(value, (p.IntValue, p.MoneyValue)):
        number = value.value if isinstance(value, p.IntValue) else value.cents
        valid = (
            schema
            == (p.Scalar.INTEGER if isinstance(value, p.IntValue) else p.Scalar.MONEY)
            and type(number) is int
        )
        budget.integer(number)
    elif isinstance(value, p.TextValue):
        valid = schema == p.Scalar.TEXT
        budget.text(value.value)
    elif isinstance(value, p.DateValue):
        valid = schema == p.Scalar.DATE and type(value.value) is date
    elif isinstance(schema, p.OptionalSchema):
        valid = isinstance(value, (p.AbsentValue, p.PresentValue))
        if isinstance(value, p.PresentValue):
            _value(value.value, schema.item, budget, depth + 1)
    elif isinstance(schema, p.RecordSchema) and isinstance(value, p.RecordValue):
        valid = value.record == schema.name
        _named(value.fields, schema.fields, budget, depth + 1)
    elif isinstance(schema, p.KeyedSchema) and isinstance(value, p.KeyedValue):
        _require(
            len(value.entries) <= budget.limits.collection_count,
            "collection_limit",
            "Collection exceeds count limit.",
        )
        budget.charge(len(value.entries), len(value.entries) * 64)
        keys: set[str] = set()
        for entry in value.entries:
            budget.text(entry.key)
            _require(entry.key not in keys, "value_type", "Duplicate collection key.")
            keys.add(entry.key)
            _value(entry.value, schema.item, budget, depth + 1)
            _require(
                any(
                    field.name == schema.key_field
                    and field.value == p.TextValue(entry.key)
                    for field in entry.value.fields
                ),
                "value_type",
                "Key differs from record identity.",
            )
        valid = True
    elif isinstance(schema, p.TaggedSchema) and isinstance(value, p.TaggedValue):
        for variant in schema.variants:
            if variant.name == value.tag:
                _value(value.value, variant.schema, budget, depth + 1)
                valid = True
    elif isinstance(schema, p.ReferenceSchema) and isinstance(
        value, p.ResolvedRefValue
    ):
        budget.text(value.key)
        valid = (
            value.record == schema.record
            and value.key_field == schema.key_field
            and bool(value.key)
        )
    elif isinstance(schema, p.UnresolvedSchema) and isinstance(
        value, p.UnresolvedTextValue
    ):
        budget.text(value.text)
        valid = True
    _require(valid, "value_type", "Value differs from declared type.")


def _named(
    values: tuple[p.NamedValue, ...],
    fields_: tuple[p.Field, ...],
    budget: _Budget,
    depth: int = 0,
) -> None:
    _require(
        len(values) == len(fields_),
        "value_type",
        "Named inputs differ from declaration.",
    )
    budget.charge(len(values), len(values) * 64)
    supplied: dict[str, p.Value] = {}
    for item in values:
        budget.text(item.name)
        _require(item.name not in supplied, "value_type", "Duplicate named input.")
        supplied[item.name] = item.value
    _require(
        supplied.keys() == {item.name for item in fields_},
        "value_type",
        "Named inputs differ from declaration.",
    )
    for field in fields_:
        _value(supplied[field.name], field.schema, budget, depth)


def _schema(
    schema: p.Schema,
    records: tuple[p.RecordSchema, ...],
    budget: _Budget,
    depth: int = 0,
) -> None:
    _require(
        depth <= budget.limits.nesting, "nesting_limit", "Schema nesting exceeds limit."
    )
    budget.charge()
    if isinstance(schema, p.OptionalSchema):
        _schema(schema.item, records, budget, depth + 1)
    elif isinstance(schema, (p.RecordSchema, p.TaggedSchema)):
        members = (
            schema.fields if isinstance(schema, p.RecordSchema) else schema.variants
        )
        _require(
            len(members) <= budget.limits.collection_count,
            "collection_limit",
            "Schema field count exceeds limit.",
        )
        names: set[str] = set()
        for member in members:
            budget.text(member.name)
            _require(
                bool(member.name.strip()) and member.name not in names,
                "schema_type",
                "Fields need unique nonempty names.",
            )
            names.add(member.name)
            _schema(member.schema, records, budget, depth + 1)
        if isinstance(schema, p.RecordSchema):
            budget.text(schema.name)
            _require(
                schema in records, "schema_type", "Record must match its declaration."
            )
        else:
            _require(bool(members), "schema_type", "Tagged schema needs variants.")
    elif isinstance(schema, p.KeyedSchema):
        _schema(schema.item, records, budget, depth + 1)
        _require(
            any(
                field.name == schema.key_field and field.schema == p.Scalar.TEXT
                for field in schema.item.fields
            ),
            "schema_type",
            "Collection key must name a text field.",
        )
    elif isinstance(schema, p.ReferenceSchema):
        _require(
            any(
                record.name == schema.record
                and any(
                    field.name == schema.key_field and field.schema == p.Scalar.TEXT
                    for field in record.fields
                )
                for record in records
            ),
            "schema_type",
            "Reference must name a declared key.",
        )


def _parse(source: str, budget: _Budget) -> ast.Module:
    _require(
        len(source) <= budget.limits.source_bytes,
        "source_limit",
        "Source exceeds byte limit.",
    )
    budget.charge(len(source), len(source) * 4)
    _require(
        len(source.encode("utf-8")) <= budget.limits.source_bytes,
        "source_limit",
        "Source exceeds byte limit.",
    )
    quote = ""
    escaped = False
    comment = False
    depth = 0
    digits = 0
    numeric_token = ""
    for character in source:
        if comment:
            comment = character != "\n"
        elif quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
        elif character in "'\"":
            quote = character
        elif character == "#":
            comment = True
        else:
            depth += int(character in "([{") - int(character in ")]}")
            _require(
                depth <= budget.limits.nesting,
                "nesting_limit",
                "Source nesting exceeds limit.",
            )
            if character.isalnum() or character == "_":
                if numeric_token or character.isdecimal():
                    numeric_token += character
                    _require(
                        len(numeric_token) <= 66,
                        "integer_limit",
                        "Integer token exceeds limit.",
                    )
            else:
                numeric_token = ""
            digits = digits + 1 if character.isdecimal() else 0
            _require(digits <= 19, "integer_limit", "Integer token exceeds limit.")
    for line in source.splitlines():
        indentation = len(line) - len(line.lstrip(" "))
        _require(
            indentation <= budget.limits.nesting * 4,
            "nesting_limit",
            "Source indentation exceeds limit.",
        )
        _require(
            "\t" not in line[: len(line) - len(line.lstrip())],
            "unsupported_syntax",
            "Indentation must use spaces.",
        )
    try:
        tree = ast.parse(source, mode="exec")
    except (SyntaxError, ValueError, RecursionError) as error:
        raise _Rejected("unsupported_syntax", "Source cannot be parsed.") from error
    pending: list[tuple[ast.AST, int]] = [(tree, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        _require(
            depth <= budget.limits.nesting,
            "nesting_limit",
            "Instruction nesting exceeds limit.",
        )
        _require(
            count <= budget.limits.ast_nodes,
            "ast_limit",
            "Instruction count exceeds limit.",
        )
        budget.charge(1, 64)
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    return tree


class _Checker:
    def __init__(
        self,
        declarations: tuple[p.FunctionDeclaration, ...],
        schemas: tuple[p.RecordSchema, ...],
        budget: _Budget,
    ) -> None:
        self.signatures = {item.function_id: item for item in declarations}
        self.records = {item.name: item for item in schemas}
        self.builtins = {item.name: item for item in BUILTINS}
        self.calls: dict[str, set[str]] = {
            item.function_id: set() for item in declarations
        }
        self.budget = budget
        self.current = ""

    def expression(self, node: ast.expr, scope: dict[str, p.Schema]) -> Expression:
        if isinstance(node, ast.Constant):
            if type(node.value) is bool:
                return Constant(p.BoolValue(node.value), p.Scalar.BOOLEAN)
            if type(node.value) is int:
                self.budget.integer(node.value)
                return Constant(p.IntValue(node.value), p.Scalar.INTEGER)
            if isinstance(node.value, str):
                self.budget.text(node.value)
                return Constant(p.TextValue(node.value), p.Scalar.TEXT)
        elif isinstance(node, ast.Name):
            _require(node.id in scope, "unknown_name", node.id)
            return Variable(node.id, scope[node.id])
        elif isinstance(node, (ast.Attribute, ast.Subscript)):
            record = self.expression(node.value, scope)
            name: str
            if isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node.slice, ast.Constant) and isinstance(
                node.slice.value, str
            ):
                name = node.slice.value
            else:
                raise _Rejected(
                    "unsupported_attribute", "Field lookup requires a literal name."
                )
            _require(
                isinstance(record.schema, p.RecordSchema), "unsupported_attribute", name
            )
            assert isinstance(record.schema, p.RecordSchema)
            for field in record.schema.fields:
                if field.name == name:
                    return FieldAccess(record, field.name, field.schema)
            raise _Rejected("unsupported_attribute", name)
        elif isinstance(node, ast.Call):
            _require(
                isinstance(node.func, ast.Name) and not node.keywords,
                "unsupported_call",
                "Only direct positional calls are supported.",
            )
            assert isinstance(node.func, ast.Name)
            arguments = tuple(self.expression(item, scope) for item in node.args)
            return self.call(node.func.id, arguments)
        elif isinstance(node, ast.BinOp):
            left, right = (
                self.expression(node.left, scope),
                self.expression(node.right, scope),
            )
            operator = OPERATORS.get(type(node.op), "unsupported")
            schema = left.schema
            valid = (
                operator in {"Add", "Sub", "Mult", "FloorDiv", "Mod"}
                and schema == right.schema == p.Scalar.INTEGER
            )
            valid |= (
                operator in {"Add", "Sub"} and schema == right.schema == p.Scalar.MONEY
            )
            valid |= (
                operator == "Mult"
                and schema == p.Scalar.MONEY
                and right.schema == p.Scalar.INTEGER
            )
            valid |= operator == "Add" and schema == right.schema == p.Scalar.TEXT
            _require(valid, "type_error", "Incompatible arithmetic operands.")
            return Operation(operator, (left, right), schema)
        elif isinstance(node, ast.UnaryOp):
            argument = self.expression(node.operand, scope)
            operator = OPERATORS.get(type(node.op), "unsupported")
            _require(
                (operator == "Not" and argument.schema == p.Scalar.BOOLEAN)
                or (
                    operator in {"USub", "UAdd"}
                    and argument.schema in (p.Scalar.INTEGER, p.Scalar.MONEY)
                ),
                "type_error",
                "Incompatible unary operand.",
            )
            return Operation(operator, (argument,), argument.schema)
        elif isinstance(node, ast.Compare):
            _require(
                len(node.ops) == 1,
                "unsupported_syntax",
                "Chained comparisons are unsupported.",
            )
            left, right = (
                self.expression(node.left, scope),
                self.expression(node.comparators[0], scope),
            )
            operator = OPERATORS.get(type(node.ops[0]), "unsupported")
            _require(
                left.schema == right.schema
                and (
                    operator in {"Eq", "NotEq"}
                    or (
                        operator in {"Lt", "LtE", "Gt", "GtE"}
                        and left.schema
                        in (
                            p.Scalar.INTEGER,
                            p.Scalar.MONEY,
                            p.Scalar.TEXT,
                            p.Scalar.DATE,
                        )
                    )
                ),
                "type_error",
                "Incompatible comparison operands.",
            )
            return Operation(operator, (left, right), p.Scalar.BOOLEAN)
        elif isinstance(node, ast.BoolOp):
            arguments = tuple(self.expression(item, scope) for item in node.values)
            _require(
                all(item.schema == p.Scalar.BOOLEAN for item in arguments),
                "type_error",
                "Boolean operands required.",
            )
            return Operation(
                OPERATORS.get(type(node.op), "unsupported"), arguments, p.Scalar.BOOLEAN
            )
        elif isinstance(node, ast.IfExp):
            condition, yes, no = (
                self.expression(item, scope)
                for item in (node.test, node.body, node.orelse)
            )
            _require(
                condition.schema == p.Scalar.BOOLEAN and yes.schema == no.schema,
                "type_error",
                "Conditional expression types differ.",
            )
            return Operation("Select", (condition, yes, no), yes.schema)
        raise _Rejected(
            "unsupported_syntax", "Instruction is outside the language allowlist."
        )

    def call(self, name: str, arguments: tuple[Expression, ...]) -> Expression:
        types = tuple(item.schema for item in arguments)
        if name in self.signatures:
            declaration = self.signatures[name]
            _require(
                types == tuple(item.schema for item in declaration.inputs),
                "type_error",
                "Call arguments differ from signature.",
            )
            self.calls[self.current].add(name)
            return Call(name, arguments, declaration.output)
        if name in self.builtins:
            builtin = self.builtins[name]
            _require(
                types == builtin.inputs,
                "type_error",
                "Builtin arguments differ from signature.",
            )
            return Call(name, arguments, builtin.output)
        if name in self.records:
            record = self.records[name]
            _require(
                types == tuple(item.schema for item in record.fields),
                "type_error",
                "Record arguments differ from fields.",
            )
            return RecordConstructor(record, arguments)
        if name == "record" and arguments:
            label = arguments[0]
            if (
                isinstance(label, Constant)
                and isinstance(label.value, p.TextValue)
                and label.value.value in self.records
            ):
                record = self.records[label.value.value]
                _require(
                    types[1:] == tuple(field.schema for field in record.fields),
                    "type_error",
                    "Record arguments differ from fields.",
                )
                return RecordConstructor(record, arguments[1:])
        if name == "tag" and len(types) == 2:
            output = self.signatures[self.current].output
            label = arguments[0]
            if (
                isinstance(output, p.TaggedSchema)
                and isinstance(label, Constant)
                and isinstance(label.value, p.TextValue)
            ):
                _require(
                    any(
                        variant.name == label.value.value and variant.schema == types[1]
                        for variant in output.variants
                    ),
                    "type_error",
                    "Tagged result differs from declaration.",
                )
                return Call(name, arguments, output)
        if name == "absent" and not types:
            output = self.signatures[self.current].output
            _require(
                isinstance(output, p.OptionalSchema),
                "type_error",
                "Absent result requires an optional return type.",
            )
            return Call(name, arguments, output)
        if name == "present" and len(types) == 1:
            return Call(name, arguments, p.OptionalSchema(types[0]))
        if (
            name == "require"
            and len(types) == 1
            and isinstance(types[0], p.OptionalSchema)
        ):
            return Call(name, arguments, types[0].item)
        if (
            name == "is_present"
            and len(types) == 1
            and isinstance(types[0], p.OptionalSchema)
        ):
            return Call(name, arguments, p.Scalar.BOOLEAN)
        if (
            name == "lookup"
            and len(types) == 2
            and isinstance(types[0], p.KeyedSchema)
            and types[1] == p.Scalar.TEXT
        ):
            return Call(name, arguments, p.OptionalSchema(types[0].item))
        if (
            name == "template"
            and len(types) == 2
            and types[0] == p.Scalar.TEXT
            and isinstance(types[1], p.RecordSchema)
            and all(field.schema == p.Scalar.TEXT for field in types[1].fields)
        ):
            return Call(name, arguments, p.Scalar.TEXT)
        raise _Rejected("unsupported_call", name)

    def block(
        self, nodes: list[ast.stmt], scope: dict[str, p.Schema], output: p.Schema
    ) -> tuple[tuple[Statement, ...], bool]:
        statements: list[Statement] = []
        returned = False
        for node in nodes:
            if isinstance(node, ast.Return) and node.value is not None:
                value = self.expression(node.value, scope)
                _require(
                    value.schema == output,
                    "return_type",
                    "Return type differs from declaration.",
                )
                statements.append(Return(value))
                returned = True
            elif (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                name = node.targets[0].id
                value = self.expression(node.value, scope)
                _require(
                    name not in scope or scope[name] == value.schema,
                    "type_error",
                    "Assignment changes variable type.",
                )
                scope[name] = value.schema
                statements.append(Assign(name, value))
            elif isinstance(node, ast.If):
                condition = self.expression(node.test, scope)
                _require(
                    condition.schema == p.Scalar.BOOLEAN,
                    "type_error",
                    "Boolean condition required.",
                )
                yes_scope, no_scope = scope.copy(), scope.copy()
                yes, yes_returns = self.block(node.body, yes_scope, output)
                no, no_returns = self.block(node.orelse, no_scope, output)
                continuing = [
                    branch
                    for branch, returns in (
                        (yes_scope, yes_returns),
                        (no_scope, no_returns),
                    )
                    if not returns
                ]
                if continuing:
                    for name, schema in continuing[0].items():
                        if all(branch.get(name) == schema for branch in continuing):
                            scope[name] = schema
                returned |= yes_returns and no_returns
                statements.append(If(condition, yes, no))
            elif (
                isinstance(node, ast.For)
                and isinstance(node.target, ast.Name)
                and not node.orelse
            ):
                collection = self.expression(node.iter, scope)
                _require(
                    isinstance(collection.schema, p.KeyedSchema),
                    "type_error",
                    "Iteration requires a finite keyed collection.",
                )
                assert isinstance(collection.schema, p.KeyedSchema)
                local = scope.copy()
                _require(
                    node.target.id not in local,
                    "type_error",
                    "Loop variable must be fresh.",
                )
                local[node.target.id] = collection.schema.item
                body, _ = self.block(node.body, local, output)
                statements.append(For(node.target.id, collection, body))
            else:
                raise _Rejected(
                    "unsupported_syntax",
                    "Instruction is outside the language allowlist.",
                )
        return tuple(statements), returned


def check_functions(
    declarations: tuple[p.FunctionDeclaration, ...],
    schemas: tuple[p.RecordSchema, ...],
    limits: Limits,
) -> CheckedFunctions | LanguageFailure:
    budget = _Budget(limits)
    path = "functions"
    try:
        _limits(limits)
        _require(
            len(declarations) <= limits.functions,
            "function_limit",
            "Function count exceeds limit.",
        )
        _require(
            len(schemas) <= limits.functions,
            "schema_limit",
            "Schema count exceeds limit.",
        )
        for schema in schemas:
            _schema(schema, schemas, budget)
        for declaration in declarations:
            budget.text(declaration.function_id)
            for item in declaration.inputs:
                budget.text(item.name)
                _require(
                    item.name.isidentifier() and not item.name.startswith("_"),
                    "function_identity",
                    "Inputs need public identifiers.",
                )
                _schema(item.schema, schemas, budget)
            _schema(declaration.output, schemas, budget)
        checker = _Checker(declarations, schemas, budget)
        reserved = set(checker.builtins) | {
            "present",
            "require",
            "is_present",
            "lookup",
            "template",
            "tag",
            "absent",
            "record",
        }
        _require(
            len(checker.records) == len(schemas),
            "duplicate_identity",
            "Record identities collide.",
        )
        names = tuple(item.function_id for item in declarations)
        _require(
            len(set(names)) == len(names)
            and not (set(names) & (reserved | set(checker.records))),
            "duplicate_identity",
            "Function identities collide.",
        )
        checked: list[CheckedFunction] = []
        for declaration in declarations:
            path = declaration.function_id
            _require(
                declaration.body.language_version == "restricted-1",
                "language_version",
                "Unsupported language version.",
            )
            _require(
                bool(declaration.function_id.strip())
                and not declaration.function_id.startswith("_"),
                "function_identity",
                "Function identity must be nonempty and public.",
            )
            checker.current = path
            tree = _parse(declaration.body.source, budget)
            scope = {item.name: item.schema for item in declaration.inputs}
            _require(
                len(scope) == len(declaration.inputs),
                "duplicate_identity",
                "Duplicate function input.",
            )
            instructions, returns = checker.block(tree.body, scope, declaration.output)
            _require(returns, "missing_return", "Every path must return a value.")
            checked.append(CheckedFunction(declaration, instructions))
        depths: dict[str, int] = {}

        def visit(name: str, active: tuple[str, ...]) -> int:
            _require(
                name not in active, "recursive_call", "Recursive calls are forbidden."
            )
            _require(
                len(active) < limits.call_depth,
                "call_depth_limit",
                "Call depth exceeds limit.",
            )
            budget.charge()
            if name not in depths:
                depth = 1
                for child in sorted(checker.calls[name]):
                    depth = max(depth, 1 + visit(child, (*active, name)))
                depths[name] = depth
            _require(
                depths[name] + len(active) <= limits.call_depth,
                "call_depth_limit",
                "Call depth exceeds limit.",
            )
            return depths[name]

        for name in names:
            visit(name, ())
        for declaration in declarations:
            _require(
                bool(declaration.tests),
                "missing_function_tests",
                "Every function requires saved tests.",
            )
            _require(
                len(declaration.tests) <= limits.collection_count,
                "collection_limit",
                "Saved test count exceeds limit.",
            )
            test_names: set[str] = set()
            for test in declaration.tests:
                budget.text(test.test_id)
                _require(
                    bool(test.test_id.strip()) and test.test_id not in test_names,
                    "duplicate_identity",
                    "Saved tests need unique names.",
                )
                test_names.add(test.test_id)
                path = declaration.function_id + "." + test.test_id
                _named(test.inputs, declaration.inputs, budget)
                _value(test.expected, declaration.output, budget)
        artifact = CheckedFunctions(tuple(checked), schemas, limits, ())
        results: list[FunctionResult] = []
        for declaration in declarations:
            for test in declaration.tests:
                path = declaration.function_id + "." + test.test_id
                result = _execute_function(
                    artifact, declaration.function_id, test.inputs, budget
                )
                if isinstance(result, LanguageFailure):
                    return result
                weight = _weight(test.expected, budget)
                budget.charge(weight * 16, weight * 8)
                _require(
                    result.value == p.normalized_value(test.expected),
                    "saved_test_failed",
                    "Saved function result differs from expected value.",
                )
                results.append(result)
        return CheckedFunctions(tuple(checked), schemas, limits, tuple(results))
    except (_Rejected, UnicodeError) as error:
        if isinstance(error, _Rejected):
            return LanguageFailure(error.code, path, error.message, budget.usage())
        return LanguageFailure(
            "invalid_text", path, "Text must encode as UTF-8.", budget.usage()
        )


class _Interpreter:
    def __init__(self, checked: CheckedFunctions, budget: _Budget) -> None:
        self.functions = {
            item.declaration.function_id: item for item in checked.functions
        }
        self.budget = budget

    def function(self, name: str, values: tuple[p.Value, ...]) -> p.Value:
        function = self.functions[name]
        self.budget.charge(1, len(values) * 32)
        scope = {
            field.name: value
            for field, value in zip(function.declaration.inputs, values, strict=True)
        }
        result = self.block(function.instructions, scope)
        assert result is not None
        return result

    def block(
        self, instructions: tuple[Statement, ...], scope: dict[str, p.Value]
    ) -> p.Value | None:
        for statement in instructions:
            self.budget.charge()
            if isinstance(statement, Assign):
                scope[statement.name] = self.expression(statement.value, scope)
            elif isinstance(statement, Return):
                return self.expression(statement.value, scope)
            elif isinstance(statement, If):
                condition = self.expression(statement.condition, scope)
                assert isinstance(condition, p.BoolValue)
                result = self.block(
                    statement.when_true if condition.value else statement.when_false,
                    scope,
                )
                if result is not None:
                    return result
            else:
                collection = self.expression(statement.collection, scope)
                assert isinstance(collection, p.KeyedValue)
                for entry in collection.entries:
                    self.budget.charge()
                    scope[statement.name] = entry.value
                    result = self.block(statement.body, scope)
                    if result is not None:
                        return result
        return None

    def expression(self, expression: Expression, scope: dict[str, p.Value]) -> p.Value:
        self.budget.charge()
        if isinstance(expression, Constant):
            _value(expression.value, expression.schema, self.budget)
            return expression.value
        if isinstance(expression, Variable):
            return scope[expression.name]
        if isinstance(expression, FieldAccess):
            record = self.expression(expression.record, scope)
            assert isinstance(record, p.RecordValue)
            self.budget.charge(len(record.fields))
            return next(
                item.value for item in record.fields if item.name == expression.name
            )
        if isinstance(expression, Operation) and expression.operator in {
            "And",
            "Or",
            "Select",
        }:
            first = self.expression(expression.arguments[0], scope)
            assert isinstance(first, p.BoolValue)
            if expression.operator == "Select":
                return self.expression(
                    expression.arguments[1 if first.value else 2], scope
                )
            value = first
            for argument in expression.arguments[1:]:
                if value.value == (expression.operator == "Or"):
                    return value
                following = self.expression(argument, scope)
                assert isinstance(following, p.BoolValue)
                value = following
            return value
        self.budget.charge(len(expression.arguments), len(expression.arguments) * 8)
        values = tuple(self.expression(item, scope) for item in expression.arguments)
        if isinstance(expression, RecordConstructor):
            self.budget.charge(len(values) * 16, len(values) * 64)
            members = tuple(
                p.NamedValue(field.name, value)
                for field, value in zip(expression.schema.fields, values, strict=True)
            )
            result = p.RecordValue(
                expression.schema.name,
                tuple(sorted(members, key=lambda item: item.name)),
            )
        elif isinstance(expression, Call):
            if expression.function in self.functions:
                return self.function(expression.function, values)
            try:
                result = self.builtin(expression.function, values)
            except _Rejected as error:
                raise _Rejected(
                    error.code, "Builtin " + expression.function + ": " + error.message
                ) from error
        else:
            result = self.operation(expression.operator, values)
        _value(result, expression.schema, self.budget)
        return result

    def operation(self, operator: str, values: tuple[p.Value, ...]) -> p.Value:
        left = values[0]
        if operator == "Not":
            assert isinstance(left, p.BoolValue)
            return p.BoolValue(not left.value)
        if operator in {"Eq", "NotEq"}:
            self.budget.charge(sum(_weight(value, self.budget) for value in values))
            equal = left == values[1]
            return p.BoolValue(equal if operator == "Eq" else not equal)
        if isinstance(left, p.TextValue):
            right = values[1]
            assert isinstance(right, p.TextValue)
            self.budget.charge(
                len(left.value) + len(right.value),
                (len(left.value) + len(right.value)) * 4,
            )
            if operator == "Add":
                _require(
                    len(left.value) + len(right.value)
                    <= self.budget.limits.string_bytes,
                    "string_limit",
                    "Text expansion exceeds limit.",
                )
                return p.TextValue(left.value + right.value)
            return p.BoolValue(_compare(operator, left.value, right.value))
        if isinstance(left, p.DateValue):
            right = values[1]
            assert isinstance(right, p.DateValue)
            return p.BoolValue(
                _compare(operator, left.value.toordinal(), right.value.toordinal())
            )
        assert isinstance(left, (p.IntValue, p.MoneyValue))
        number = left.value if isinstance(left, p.IntValue) else left.cents
        if operator in {"USub", "UAdd"}:
            result = -number if operator == "USub" else number
        else:
            right = values[1]
            assert isinstance(right, (p.IntValue, p.MoneyValue))
            other = right.value if isinstance(right, p.IntValue) else right.cents
            if operator in {"Lt", "LtE", "Gt", "GtE"}:
                return p.BoolValue(_compare(operator, number, other))
            if operator == "Mult":
                _require(
                    other == 0
                    or abs(number)
                    <= self.budget.limits.integer_magnitude // abs(other),
                    "integer_limit",
                    "Multiplication exceeds magnitude limit.",
                )
                result = number * other
            elif operator == "Add":
                result = number + other
            elif operator == "Sub":
                result = number - other
            else:
                _require(other != 0, "division_by_zero", "Division by zero.")
                result = number // other if operator == "FloorDiv" else number % other
        return (
            p.IntValue(result) if isinstance(left, p.IntValue) else p.MoneyValue(result)
        )

    def builtin(self, name: str, values: tuple[p.Value, ...]) -> p.Value:
        size = sum(_weight(value, self.budget) for value in values)
        self.budget.charge(size, size * 4 + 32)
        if name == "absent":
            return p.AbsentValue()
        first = values[0]
        if name == "tag":
            assert isinstance(first, p.TextValue)
            return p.TaggedValue(first.value, values[1])
        if name == "present":
            return p.PresentValue(first)
        if name == "is_present":
            return p.BoolValue(isinstance(first, p.PresentValue))
        if name == "require":
            _require(
                isinstance(first, p.PresentValue),
                "missing_value",
                "Required optional value is absent.",
            )
            assert isinstance(first, p.PresentValue)
            return first.value
        if name == "lookup":
            assert isinstance(first, p.KeyedValue) and isinstance(
                values[1], p.TextValue
            )
            for entry in first.entries:
                if entry.key == values[1].value:
                    return p.PresentValue(entry.value)
            return p.AbsentValue()
        if name == "money":
            assert isinstance(first, p.IntValue)
            return p.MoneyValue(first.value)
        if name in {"cents", "format_money"}:
            assert isinstance(first, p.MoneyValue)
            if name == "cents":
                return p.IntValue(first.cents)
            return p.TextValue(
                ("-" if first.cents < 0 else "")
                + f"{abs(first.cents) // 100}.{abs(first.cents) % 100:02d}"
            )
        if name == "date":
            assert all(isinstance(value, p.IntValue) for value in values)
            numbers = tuple(
                value.value for value in values if isinstance(value, p.IntValue)
            )
            return p.DateValue(date(*numbers))
        if isinstance(first, p.DateValue):
            if name == "add_days":
                assert isinstance(values[1], p.IntValue)
                return p.DateValue(first.value + timedelta(days=values[1].value))
            if name == "days_between":
                assert isinstance(values[1], p.DateValue)
                return p.IntValue((first.value - values[1].value).days)
            if name == "format_date":
                return p.TextValue(first.value.isoformat())
            return p.IntValue(
                {
                    "year": first.value.year,
                    "month": first.value.month,
                    "day": first.value.day,
                }[name]
            )
        assert isinstance(first, p.TextValue)
        text = first.value
        if name in {"starts_with", "contains"}:
            assert isinstance(values[1], p.TextValue)
            return p.BoolValue(
                text.startswith(values[1].value)
                if name == "starts_with"
                else values[1].value in text
            )
        if name == "trim":
            return p.TextValue(text.strip())
        if name == "parse_money":
            sign = -1 if text.startswith("-") else 1
            digits = text[1:] if sign < 0 else text
            whole, dot, fraction = digits.partition(".")
            _require(
                bool(whole)
                and whole.isascii()
                and whole.isdecimal()
                and dot == "."
                and len(fraction) == 2
                and fraction.isascii()
                and fraction.isdecimal()
                and len(whole) <= 17,
                "parse_error",
                "Money requires decimal digits and exactly two fractional digits.",
            )
            return p.MoneyValue(sign * (int(whole) * 100 + int(fraction)))
        if name in {"parse_iso_date", "parse_us_date"}:
            separator = "-" if name == "parse_iso_date" else "/"
            parts = text.split(separator)
            sizes = (4, 2, 2) if separator == "-" else (2, 2, 4)
            _require(
                len(parts) == 3
                and all(
                    len(part) == size and part.isascii() and part.isdecimal()
                    for part, size in zip(parts, sizes, strict=True)
                ),
                "parse_error",
                "Date format differs from declared parser.",
            )
            numbers = tuple(int(part) for part in parts)
            year, month, day = (
                numbers if separator == "-" else (numbers[2], numbers[0], numbers[1])
            )
            return p.DateValue(date(year, month, day))
        if name == "between":
            assert isinstance(values[1], p.TextValue) and isinstance(
                values[2], p.TextValue
            )
            prefix, suffix = values[1].value, values[2].value
            _require(
                bool(prefix)
                and bool(suffix)
                and text.count(prefix) == 1
                and text.count(suffix) == 1,
                "parse_error",
                "Delimiters must occur exactly once.",
            )
            start = text.index(prefix) + len(prefix)
            end = text.index(suffix)
            _require(end >= start, "parse_error", "Delimiter order is invalid.")
            self.budget.charge(end - start, (end - start) * 4)
            return p.TextValue(text[start:end])
        assert name == "template" and isinstance(values[1], p.RecordValue)
        facts = {field.name: field.value for field in values[1].fields}
        parts: list[str] = []
        offset = 0
        size = 0
        while offset < len(text):
            self.budget.charge()
            if text[offset] == "{":
                end = text.find("}", offset + 1)
                _require(end >= 0, "template_error", "Unclosed placeholder.")
                key = text[offset + 1 : end]
                _require(
                    key in facts,
                    "template_error",
                    "Placeholder must name a declared fact.",
                )
                fact = facts[key]
                assert isinstance(fact, p.TextValue)
                part = fact.value
                offset = end + 1
            else:
                _require(
                    text[offset] != "}", "template_error", "Unmatched closing brace."
                )
                part = text[offset]
                offset += 1
            size += len(part)
            _require(
                size <= self.budget.limits.string_bytes,
                "string_limit",
                "Template expansion exceeds limit.",
            )
            self.budget.charge(len(part) + 1, len(part) * 4 + 16)
            parts.append(part)
        self.budget.charge(size, size * 4)
        return p.TextValue("".join(parts))


def _compare(operator: str, left: int | str, right: int | str) -> bool:
    assert type(left) is type(right)
    if isinstance(left, int):
        assert isinstance(right, int)
        return {
            "Lt": left < right,
            "LtE": left <= right,
            "Gt": left > right,
            "GtE": left >= right,
        }[operator]
    assert isinstance(right, str)
    return {
        "Lt": left < right,
        "LtE": left <= right,
        "Gt": left > right,
        "GtE": left >= right,
    }[operator]


def _weight(value: p.Value, budget: _Budget) -> int:
    budget.charge()
    if isinstance(value, p.TextValue):
        budget.charge(len(value.value))
        return len(value.value) + 1
    if isinstance(value, p.RecordValue):
        return 1 + sum(
            len(item.name) + _weight(item.value, budget) for item in value.fields
        )
    if isinstance(value, p.KeyedValue):
        return 1 + sum(
            len(item.key) + _weight(item.value, budget) for item in value.entries
        )
    if isinstance(value, (p.PresentValue, p.TaggedValue)):
        return 1 + _weight(value.value, budget)
    return 1


def _execute_function(
    checked: CheckedFunctions,
    function_id: str,
    inputs: tuple[p.NamedValue, ...],
    ledger: _Budget,
) -> FunctionResult | LanguageFailure:
    try:
        _limits(ledger.limits)
        ledger.charge(
            len(checked.functions) + len(checked.schemas),
            (len(checked.functions) + len(checked.schemas)) * 64,
        )
        interpreter = _Interpreter(checked, ledger)
        _require(function_id in interpreter.functions, "unknown_function", function_id)
        declaration = interpreter.functions[function_id].declaration
        _named(inputs, declaration.inputs, ledger)
        ledger.charge(
            sum(_weight(item.value, ledger) for item in inputs) * 16,
            sum(_weight(item.value, ledger) for item in inputs) * 8,
        )
        values = {item.name: p.normalized_value(item.value) for item in inputs}
        result = interpreter.function(
            function_id, tuple(values[field.name] for field in declaration.inputs)
        )
        _value(result, declaration.output, ledger)
        ledger.charge(_weight(result, ledger) * 16, _weight(result, ledger) * 8)
        return FunctionResult(p.normalized_value(result), ledger.usage())
    except _Rejected as error:
        return LanguageFailure(error.code, function_id, error.message, ledger.usage())
    except (ValueError, OverflowError, UnicodeError) as error:
        return LanguageFailure("parse_error", function_id, str(error), ledger.usage())


def execute_function(
    checked: CheckedFunctions,
    function_id: str,
    inputs: tuple[p.NamedValue, ...],
    budget: Limits,
) -> FunctionResult | LanguageFailure:
    return _execute_function(checked, function_id, inputs, _Budget(budget))
