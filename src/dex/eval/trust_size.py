from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any

from dex import codec
from dex.core import authority as a
from dex.core import events as e
from dex.core import runtime as r
from dex.eval.trust_fixture import NOW, POLICY, TrustFixture, program


def _case_events(
    template: tuple[e.RuntimeEvent, ...], case_id: str, revision: int
) -> tuple[e.RuntimeEvent, ...]:
    result: list[e.RuntimeEvent] = []
    command_id = "start/" + case_id
    for event in template:
        payload = event.payload
        if isinstance(payload, e.BatchStarted):
            command = payload.command
            assert isinstance(command, e.StartSandbox)
            payload = e.BatchStarted(
                replace(
                    command,
                    case_id=case_id,
                    meta=replace(
                        command.meta, command_id=command_id, expected_revision=revision
                    ),
                )
            )
        elif isinstance(payload, (e.WorkOpened, e.InputBound, e.WorkSucceeded)):
            payload = replace(
                payload, address=replace(payload.address, case_id=case_id)
            )
        elif isinstance(payload, e.CaseSettled):
            payload = replace(payload, case_id=case_id)
        else:
            assert isinstance(payload, e.BatchCompleted), type(payload)
        result.append(replace(event, command_id=command_id, payload=payload))
    return tuple(result)


def run_size(out: Path) -> dict[str, Any]:
    fixture = TrustFixture(out)
    try:
        fixture.train()
        pin = fixture.register(program(pure=True))
        start = e.StartSandbox(
            fixture.meta("template"),
            "template",
            pin,
            fixture.state.cases["training-0"].start.facts,
            NOW.date(),
            company=POLICY,
        )
        prototype = r.decide(fixture.state, start, fixture.workspace.catalog)
        assert isinstance(prototype, r.Accepted), prototype
        additions: list[e.RuntimeEvent] = []
        initial_revision = fixture.state.revision
        for index in range(9700):
            name = "review-case-" + str(index)
            additions.extend(
                _case_events(prototype.events, name, initial_revision + len(additions))
            )
        for index in range(9700):
            name = "review-case-" + str(index)
            identity = "review/" + name
            command = e.ReviewResults(
                e.CommandMeta(
                    identity, "operator", NOW, NOW, initial_revision + len(additions)
                ),
                name,
                (
                    a.ReviewedResult(
                        e.WorkRevision(e.WorkAddress(name, "calculate"), 1), "clean"
                    ),
                ),
                fixture.action(identity),
            )
            additions.append(
                e.RuntimeEvent(identity, 0, e.WorkspaceTransitioned(command))
            )
        prefix = tuple(
            codec.loads(raw, e.RuntimeEvent)
            for (raw,) in fixture.workspace.connection.execute(
                "SELECT payload FROM events ORDER BY revision"
            )
        )
        events = (*prefix, *additions)
        begun = perf_counter()
        state = r.rebuild(events, fixture.workspace.catalog)
        reduced = perf_counter()
        review_events = sum(
            isinstance(event.payload, e.EffectTransitioned)
            and isinstance(event.payload.command, e.ApproveEffect)
            or isinstance(event.payload, e.WorkspaceTransitioned)
            and isinstance(event.payload.command, e.ReviewResults)
            for event in events
        )
        assert review_events == 10000
        assert fixture.count("calculate", state) == 10000
        assert fixture.count("write", state) == 300
        connection = fixture.workspace.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.executemany(
                "INSERT INTO events VALUES (?, ?)",
                (
                    (initial_revision + index + 1, codec.dumps(event))
                    for index, event in enumerate(additions)
                ),
            )
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        saved = perf_counter()
        count, maximum = connection.execute(
            "SELECT count(*), max(revision) FROM events"
        ).fetchone()
        assert count == maximum == state.revision
        fixture.workspace.state = state
        del events, additions, prefix, prototype, state
        sampling_start = perf_counter()
        fixture.grant()
        for index in range(1, 21):
            fixture.start("eligible-" + str(index), amount=500_000)
        sampling_end = perf_counter()
        sample = fixture.state.case_samples["eligible-20"]
        assert sample == a.CaseSample(20, True)
        assert fixture.dispatch(fixture.ref("eligible-20")) == r.Refused(
            "sample_review_required"
        )
        assert isinstance(fixture.dispatch(fixture.ref("eligible-1")), r.Accepted)
        fixture.start("above", amount=500_001)
        assert fixture.dispatch(fixture.ref("above")) == r.Refused(
            "exact_approval_required"
        )
        fixture.revoke()
        assert fixture.dispatch(fixture.ref("eligible-2")) == r.Refused(
            "exact_approval_required"
        )
        reopening = perf_counter()
        equal = fixture.reopen()
        reopened = perf_counter()
        return {
            "review_events": review_events,
            "calculation_count": fixture.count("calculate"),
            "writing_count": fixture.count("write"),
            "ordinal": fixture.state.sampling_ordinals[POLICY.company_id],
            "sampled_case": "eligible-20",
            "grant_checks": True,
            "revocation_preserved": "grant" in fixture.state.revoked_grants,
            "reopen_equal": equal,
            "writes": fixture.adapter.writes(),
            "cases": len(fixture.state.cases),
            "revision": fixture.state.revision,
            "timing_seconds": {
                "core_accounting": reduced - begun + sampling_end - sampling_start,
                "event_reduction": reduced - begun,
                "save": saved - reduced,
                "reopen": reopened - reopening,
                "sampling_and_grant": sampling_end - sampling_start,
            },
        }
    finally:
        fixture.workspace.close()
