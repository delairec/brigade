from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.collect_document import CollectionRequest, collect_document
from brigade.collecting.collector_environment import CollectorInputs
from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import BrigadeError
from brigade.inbox.fingerprint_check_run import fingerprint_check_run
from brigade.inbox.read_inbox import read_inbox
from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.runtime import Runtime
from brigade.system.validate_document import DocumentInvalid, Field, validate_document

SIGNAL_KIND = "check_run"
NO_PARAMETERS = {}
CACHE_HONOURED = False
CHECK_RUN_SHAPE = {
    "pull_request": Field(kinds=(int,), nullable=True),
    "branch": Field(kinds=(str,)),
    "name": Field(kinds=(str,)),
    "head": Field(kinds=(str,)),
}


@dataclass(frozen=True)
class CheckRunsRecording:
    project: str
    path: Path
    collector: object
    equipment: CollectorEquipment


def _read_check_run(collector: object, item: dict) -> dict:
    try:
        validate_document(item, CHECK_RUN_SHAPE)
    except DocumentInvalid as problem:
        raise BrigadeError(f"collector {collector.name} answered a check run that {problem}") from None
    return item


def record_check_runs(runtime: Runtime, recording: CheckRunsRecording) -> None:
    collection = collect_document(
        recording.collector,
        CollectionRequest(
            inputs=CollectorInputs(project=recording.path, since=runtime.now.date(), parameters=NO_PARAMETERS),
            refresh=CACHE_HONOURED,
            equipment=recording.equipment,
        ),
        runtime,
    )
    held = {signal.fingerprint for signal in read_inbox(runtime.paths.state_root, runtime.now)}
    for item in collection.document["items"]:
        check_run = _read_check_run(recording.collector, item)
        fingerprint = fingerprint_check_run(recording.project, check_run)
        if fingerprint not in held:
            record_signal(
                runtime.paths,
                runtime.now,
                NewSignal(kind=SIGNAL_KIND, project=recording.project, fingerprint=fingerprint, evidence=check_run),
            )
            held.add(fingerprint)
