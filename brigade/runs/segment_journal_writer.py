import json
from datetime import UTC, datetime
from pathlib import Path

from brigade.runs.plan_run import RunPlan
from brigade.runs.run_locations import JOURNAL_FILE
from brigade.runtime import Runtime
from brigade.system.actions_request import ActionsRequest
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion

DOCUMENT_SCHEMA_VERSION = 1
SUMMARY_LIMIT = 200
RAW_KIND = "raw"
JOURNAL_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
LINE_END = b"\n"


class SegmentJournalWriter:
    def __init__(self, plan: RunPlan, number: int, runtime: Runtime, output: Path):
        self._plan = plan
        self._number = number
        self._runtime = runtime
        self._output = output
        self._offset = 0

    def write_complete_lines(self) -> None:
        new_output = self._read_new_output()
        self._write(new_output[: new_output.rfind(LINE_END) + 1])

    def write_rest(self) -> None:
        self._write(self._read_new_output())

    def _read_new_output(self) -> bytes:
        with self._output.open("rb") as stream:
            stream.seek(self._offset)
            return stream.read()

    def _read_actions(self, output: str) -> list[tuple[str, str]]:
        if not self._plan.reads_actions:
            return [(RAW_KIND, line) for line in output.splitlines()]
        question = ClientQuestion(self._plan.client, ActionsRequest(output=output))
        answer = ask_named_client(self._plan.client_adapter, question, self._plan.configuration, self._runtime)
        return [(action.kind, action.summary) for action in answer.actions]

    def _describe_record(self, at: str, kind: str, summary: str) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "at": at,
            "segment": self._number,
            "kind": kind,
            "summary": summary[:SUMMARY_LIMIT],
            "cut": len(summary) > SUMMARY_LIMIT,
        }

    def _write(self, chunk: bytes) -> None:
        if not chunk:
            return
        self._offset += len(chunk)
        actions = self._read_actions(chunk.decode("utf-8", errors="replace"))
        at = datetime.now(UTC).strftime(JOURNAL_INSTANT_FORMAT)
        with (self._plan.run_directory / JOURNAL_FILE).open("a", encoding="utf-8") as journal:
            journal.writelines(json.dumps(self._describe_record(at, kind, summary)) + "\n" for kind, summary in actions)
