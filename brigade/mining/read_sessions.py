import json
from dataclasses import dataclass
from datetime import UTC, datetime, time

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.run_finished import RunFinished
from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.transcripts_answer import TranscriptMessage
from brigade.system.transcripts_request import TranscriptsRequest


@dataclass(frozen=True)
class SessionRead:
    finished: RunFinished
    messages: tuple[TranscriptMessage, ...]


@dataclass(frozen=True)
class SessionsRead:
    sessions: tuple[SessionRead, ...]
    unreadable: tuple[dict, ...]


def _read_worktree(runtime: Runtime, run: str) -> str:
    record = runtime.paths.state_root / RUNS_DIRECTORY / run / RUN_RECORD_FILE
    if not record.is_file():
        raise BrigadeError(f"run {run}: no run record, its directory was pruned")
    return json.loads(record.read_text(encoding="utf-8"))["worktree"]


def _read_messages(finished: RunFinished, runtime: Runtime, equipment: CollectorEquipment):
    request = TranscriptsRequest(session_id=finished.session, worktree=_read_worktree(runtime, finished.run))
    question = ClientQuestion(finished.client, request)
    client = equipment.resolve_client(finished.client)
    try:
        return ask_named_client(client, question, equipment.configuration, runtime).messages
    except BrigadeError as error:
        raise BrigadeError(f"client adapter {finished.client}: {error}") from None


def read_sessions(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> SessionsRead:
    start = datetime.combine(read_collector_environment(environment).since, time(), tzinfo=UTC)
    last_finished = {}
    for entry in read_ledger(runtime.paths.state_root).entries:
        finished = entry.event
        if entry.instant < start or finished.name != RunFinished.name or finished.session is None:
            continue
        last_finished[(finished.client, finished.session)] = finished
    sessions = []
    unreadable = []
    for finished in last_finished.values():
        try:
            sessions.append(SessionRead(finished, _read_messages(finished, runtime, equipment)))
        except BrigadeError as error:
            unreadable.append({"run": finished.run, "session": finished.session, "reason": str(error)})
    return SessionsRead(sessions=tuple(sessions), unreadable=tuple(unreadable))
