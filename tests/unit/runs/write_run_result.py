import dataclasses
import json
from pathlib import Path

from brigade.ledger.declared_events import RUN_FINISHED_SCHEMA_VERSION
from tests.unit.ledger.create_run_finished import create_run_finished


def write_run_result(
    path: Path,
    outcome: str = "done",
    *,
    message: str | None = None,
    session: str | None = None,
    main_turns: int | None = None,
    client: str = "claude-code",
    ts: str | None = None,
    cost_usd: float | None = None,
    duration_ms: int | None = 1000,
) -> Path:
    finished = dataclasses.replace(
        create_run_finished(path.parent.name, outcome=outcome, main_turns=main_turns, client=client),
        message=message,
        session=session,
        cost_usd=cost_usd,
        duration_ms=duration_ms,
    )
    instant = {} if ts is None else {"ts": ts}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": RUN_FINISHED_SCHEMA_VERSION, **instant, **finished.to_document()}))
    return path
