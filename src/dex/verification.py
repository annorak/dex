from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from typing import cast

from dex.core import events as e
from dex.core import language as lang
from dex.core import program as p
from dex.core import runtime as r


@dataclass(frozen=True)
class VerifiedProgram:
    artifact: p.StructuralArtifact
    missing_checks: tuple[p.MissingCheck, ...] = ()


def verify_registration(
    draft: p.ProgramDraft, sources: p.SourceCatalog, at: datetime
) -> VerifiedProgram | p.ExecutionPending | p.StructuralFailure:
    result = p.verify_program(draft, sources, lang.DEFAULT_LIMITS)
    if isinstance(result, p.StructuralFailure):
        return result
    catalog = r.ProgramCatalog(
        (r.ArtifactEntry(r.artifact_pin(result.artifact), result.artifact),)
    )
    pin = catalog.entries[0].pin
    nodes = catalog.nodes[pin]
    if draft.rules or any(
        isinstance(node, (p.AiStep, p.HumanStep))
        or isinstance(node, p.CodeStep)
        and node.metadata.changes
        for node in nodes.values()
    ):
        return result
    pending: list[object] = [draft]
    while pending:
        value = pending.pop()
        if isinstance(
            value,
            (
                p.ReferenceSchema,
                p.ResolvedRefValue,
                p.UnresolvedSchema,
                p.UnresolvedTextValue,
            ),
        ):
            return result
        if isinstance(value, tuple):
            pending.extend(cast(tuple[object, ...], value))
        elif is_dataclass(value) and not isinstance(value, type):
            pending.extend(getattr(value, item.name) for item in fields(value))
    if not draft.scenarios:
        return result
    covered: set[str] = set()
    for scenario in draft.scenarios:
        initial = r.rebuild((), catalog)
        command = e.StartSandbox(
            e.CommandMeta(scenario.scenario_id, "verifier", at, at, 0),
            scenario.scenario_id,
            pin,
            scenario.inputs,
            at.date(),
        )
        execution = r.decide(initial, command, catalog)
        if isinstance(execution, r.Refused):
            return result
        work = execution.state.work[
            e.WorkAddress(scenario.scenario_id, p.node_identity(draft.root))
        ]
        if (
            work.completed is None
            or work.completed.value != scenario.expected
            or r.rebuild(execution.events, catalog) != execution.state
        ):
            return result
        covered.update(address.node_id for address in execution.state.work)
    if covered != set(nodes):
        return result
    return VerifiedProgram(result.artifact)
