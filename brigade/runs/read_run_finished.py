from dataclasses import MISSING, fields
from pathlib import Path

from brigade.ledger.declared_events import RUN_FINISHED_SCHEMA_VERSION
from brigade.ledger.read_ledger import DECLARED_FIELD
from brigade.ledger.run_finished import RunFinished
from brigade.runs.read_run_document import read_run_document
from brigade.runs.run_record import RunRecord
from brigade.runs.upgrade_run_result import RESULT_SCHEMA_VERSION_1, SCHEMA_1_SHAPE, upgrade_run_result
from brigade.system.validate_document import Field

VERSION_SHAPE = {"schema_version": Field((int,), values=(RESULT_SCHEMA_VERSION_1, RUN_FINISHED_SCHEMA_VERSION))}
RUN_FINISHED_SHAPE = {field.name: DECLARED_FIELD for field in fields(RunFinished) if field.default is MISSING}


def read_run_finished(path: Path, kind_name: str, record: RunRecord, segment: int) -> RunFinished:
    version = read_run_document(path, kind_name, VERSION_SHAPE)["schema_version"]
    if version == RESULT_SCHEMA_VERSION_1:
        document = upgrade_run_result(read_run_document(path, kind_name, SCHEMA_1_SHAPE), record, segment)
    else:
        document = read_run_document(path, kind_name, RUN_FINISHED_SHAPE)
    return RunFinished.from_document(document)
