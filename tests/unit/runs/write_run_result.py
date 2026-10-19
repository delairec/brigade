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
    main_steps: int | None = None,
) -> Path:
    finished = dataclasses.replace(
        create_run_finished(path.parent.name, outcome=outcome, main_steps=main_steps), message=message, session=session
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": RUN_FINISHED_SCHEMA_VERSION, **finished.to_document()}))
    return path
