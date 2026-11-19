import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from brigade.errors import BrigadeError

READY_FIELD = "awawa"
DOCUMENT_FIELD = "document"
ERROR_FIELD = "error"
OK = 200
NOT_FOUND = 404
SERVER_ERROR = 500
UNAVAILABLE = 503
NO_ANSWER = ""


class AddonChild(Protocol):
    def send(self, line: str) -> None: ...

    def receive(self, timeout_s: float) -> str | None: ...

    def is_running(self) -> bool: ...

    def describe_failure(self) -> str: ...

    def stop(self) -> None: ...


@dataclass(frozen=True)
class AddonAnswer:
    status: int
    document: dict


def _decode(line: str) -> dict:
    try:
        decoded = json.loads(line)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _answer_unavailable(reason: str) -> AddonAnswer:
    return AddonAnswer(status=UNAVAILABLE, document={ERROR_FIELD: f"the awawa addon {reason}"})


class AwawaAddonSupervisor:
    def __init__(self, holders: frozenset[str], start_child: Callable[[], AddonChild], answer_timeout_s: float):
        self.holders = holders
        self.start_child = start_child
        self.answer_timeout_s = answer_timeout_s
        self.child: AddonChild | None = None
        self.lock = threading.Lock()

    def open(self) -> None:
        if self.holders:
            with self.lock:
                self._start()

    def ask(self, project: str, query: dict) -> AddonAnswer:
        if project not in self.holders:
            return AddonAnswer(status=NOT_FOUND, document={ERROR_FIELD: f"@PROJECT.{project} holds no awawa corpus"})
        with self.lock:
            return self._ask({"project": project, **query})

    def stop(self) -> None:
        with self.lock:
            self._discard()

    def _ask(self, message: dict) -> AddonAnswer:
        if self.child is None or not self.child.is_running():
            self._discard()
            failure = self._start()
            if failure is not None:
                return _answer_unavailable(f"did not start: {failure}")
        self.child.send(f"{json.dumps(message)}\n")
        line = self.child.receive(self.answer_timeout_s)
        if line is None:
            silent = self.child.is_running()
            self._discard()
            reason = f"answered nothing within {self.answer_timeout_s:g} s" if silent else "stopped"
            return _answer_unavailable(f"{reason}; the next request starts it again")
        answer = _decode(line)
        if DOCUMENT_FIELD in answer:
            return AddonAnswer(status=OK, document=answer[DOCUMENT_FIELD])
        if ERROR_FIELD in answer:
            return AddonAnswer(status=SERVER_ERROR, document={ERROR_FIELD: answer[ERROR_FIELD]})
        self._discard()
        return _answer_unavailable("answered no document; the next request starts it again")

    def _start(self) -> str | None:
        try:
            child = self.start_child()
        except BrigadeError as error:
            return str(error)
        if READY_FIELD in _decode(child.receive(self.answer_timeout_s) or NO_ANSWER):
            self.child = child
            return None
        child.stop()
        return child.describe_failure()

    def _discard(self) -> None:
        if self.child is not None:
            self.child.stop()
            self.child = None
