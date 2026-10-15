from pathlib import Path

from brigade.ledger.declare_event_shape import declare_event_shape
from brigade.ledger.declared_events import RUN_FINISHED_SCHEMA_VERSION
from brigade.ledger.run_finished import RunFinished
from brigade.runs.read_run_document import read_run_document
from brigade.system.validate_document import Field

RUN_FINISHED_SHAPE = {
    "schema_version": Field((int,), values=(RUN_FINISHED_SCHEMA_VERSION,)),
    **declare_event_shape(RunFinished),
}


def read_run_finished(path: Path, kind_name: str) -> RunFinished:
    return RunFinished.from_document(read_run_document(path, kind_name, RUN_FINISHED_SHAPE))
