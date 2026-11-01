import dataclasses
import json
import re
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.transcript_findings import collect
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.run_finished import RunFinished
from brigade.system.parse_configuration import Configuration
from brigade.system.token_usage import TokenUsage
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

ENVIRONMENT = {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-20", "BRIGADE_PARAMS": "{}"}
BEFORE_THE_WINDOW = datetime(2026, 10, 19, 23, 0, tzinfo=UTC)
IN_THE_WINDOW = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
NOW = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
NOT_CACHED = False
BRIEF = {"role": "user", "timestamp": None, "content": "Deliver B42.", "tool_calls": 0, "id": None, "usage": None}
ANSWER = {
    "role": "assistant",
    "timestamp": None,
    "content": [{"type": "text", "text": "Done."}],
    "tool_calls": 0,
    "id": None,
    "usage": None,
}


def _finish(run: str, session: str | None, task: str | None = "B42") -> RunFinished:
    return RunFinished(
        run=run,
        segment=1,
        procedure="build-task",
        slot="build",
        role="ada",
        client="vibe",
        project="oak",
        session=session,
        main_steps=12,
        total_steps=12,
        duration_ms=60000,
        usage=TokenUsage(
            input_tokens=10, output_tokens=200, cache_creation_input_tokens=0, cache_read_input_tokens=3000
        ),
        outcome="done",
        error_class=None,
        exit=0,
        wave="oak_w3",
        task=task,
        nulls={},
        cost_usd=0.42,
    )


class TranscriptsClientDouble:
    def __init__(self, transcripts: dict):
        self.transcripts = transcripts
        self.worktrees = []

    def answer(self, operation: str, request: dict) -> dict:
        self.worktrees.append(request["worktree"])
        if request["session_id"] not in self.transcripts:
            raise BrigadeError(f"no transcript of session {request['session_id']}")
        return {"schema_version": 1, "messages": self.transcripts[request["session_id"]], "subagents": []}


def _call(command: str) -> dict:
    return {
        "role": "assistant",
        "timestamp": None,
        "content": [],
        "tool_calls": 1,
        "id": None,
        "usage": None,
        "calls": [command],
    }


def _result(*, refused: bool, truncated: str | None) -> dict:
    return {
        "role": "user",
        "timestamp": None,
        "content": [],
        "tool_calls": 0,
        "id": None,
        "usage": None,
        "results": [{"refused": refused, "truncated": truncated}],
    }


REFUSED = True
TRUNCATED_TO_B1 = "/srv/state/tool-results/b1.txt"
CORRECTION = {**BRIEF, "content": "Not that file: the spec."}


def _find(detector: str, position: int) -> dict:
    return {
        "detector": detector,
        "client": "vibe",
        "session": "s-built",
        "run": "r3",
        "position": position,
        "fingerprint": f"{detector}:vibe:s-built:{position}",
        "cost_usd": 0.42,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 200,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 3000,
        },
    }


class TranscriptFindingsCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), now=NOW, run_process=self.processes)
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})
        run_directory = self.runtime.paths.state_root / "runs" / "r3"
        run_directory.mkdir(parents=True)
        (run_directory / "run.json").write_text(
            json.dumps({"run": "r3", "worktree": "/srv/oak/.brigade/worktrees/B42"})
        )
        append_event(self.runtime.paths, IN_THE_WINDOW, _finish("r3", "s-built"))

    def collect(self, messages: list) -> dict:
        client = TranscriptsClientDouble({"s-built": messages})
        equipment = CollectorEquipment(
            configuration=Configuration(), forge=None, forge_name="github", resolve_client=lambda name: client
        )
        return collect(ENVIRONMENT, self.runtime, equipment)

    def test_should_find_each_user_message_after_the_first_of_its_session_as_a_correction(self):
        # Act
        document = self.collect([BRIEF, _call("Bash ls"), _result(refused=not REFUSED, truncated=None), CORRECTION])

        # Assert
        self.assertEqual(document["items"], [_find("correction", 4)])

    def test_should_find_each_tool_result_marked_refused_as_a_refusal(self):
        # Act
        document = self.collect([BRIEF, _call("Bash rm -rf build"), _result(refused=REFUSED, truncated=None)])

        # Assert
        self.assertEqual(document["items"], [_find("refusal", 3)])

    def test_should_find_a_command_run_three_times_once_at_its_third_run(self):
        # Arrange
        status = _call("Bash git status")

        # Act
        document = self.collect([BRIEF, status, _call("Bash git log"), status, status, status])

        # Assert
        self.assertEqual(document["items"], [_find("repeated_command", 5)])

    def test_should_find_a_call_naming_the_place_of_a_truncated_output_as_an_oversized_re_read(self):
        # Act
        document = self.collect(
            [
                BRIEF,
                _call("Read /srv/state/tool-results/b0.txt"),
                _call("Bash git log"),
                _result(refused=not REFUSED, truncated=TRUNCATED_TO_B1),
                _call(f"Read {TRUNCATED_TO_B1}"),
            ]
        )

        # Assert
        self.assertEqual(document["items"], [_find("oversized_re_read", 5)])

    def test_should_declare_its_document_not_cached(self):
        # Act
        document = self.collect([BRIEF])

        # Assert
        self.assertIs(document["cache"], NOT_CACHED)

    def test_should_leave_no_identifier_a_private_pattern_or_a_built_in_matches(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("PRIVATE", r"s-\w+"))}
        )

        # Act
        document = self.collect([BRIEF, CORRECTION])

        # Assert
        self.assertNotRegex(json.dumps(document), re.compile(r"s-built"))

    def test_should_find_no_re_read_after_a_tool_output_left_whole(self):
        # Act
        document = self.collect([BRIEF, _result(refused=not REFUSED, truncated=None), _call("Bash git log")])

        # Assert
        no_findings = []
        self.assertEqual(document["items"], no_findings)

    def test_should_carry_no_usage_for_a_run_whose_usage_was_not_measured(self):
        # Arrange
        unmeasured = dataclasses.replace(_finish("r3", "s-built"), run="r5", usage=None)
        run_directory = self.runtime.paths.state_root / "runs" / "r5"
        run_directory.mkdir(parents=True)
        (run_directory / "run.json").write_text(
            json.dumps({"run": "r5", "worktree": "/srv/oak/.brigade/worktrees/B42"})
        )
        append_event(self.runtime.paths, IN_THE_WINDOW, unmeasured)

        # Act
        document = self.collect([BRIEF, CORRECTION])

        # Assert
        self.assertEqual(
            document["items"],
            [
                {
                    "detector": "correction",
                    "client": "vibe",
                    "session": "s-built",
                    "run": "r5",
                    "position": 2,
                    "fingerprint": "correction:vibe:s-built:2",
                    "cost_usd": 0.42,
                    "usage": None,
                }
            ],
        )

    def test_should_read_a_session_once_from_the_last_run_finished_naming_it(self):
        # Arrange
        second_segment = dataclasses.replace(_finish("r3", "s-built"), segment=2, cost_usd=0.3)
        append_event(self.runtime.paths, IN_THE_WINDOW, second_segment)

        # Act
        document = self.collect([BRIEF, CORRECTION])

        # Assert
        self.assertEqual(document["items"], [{**_find("correction", 2), "cost_usd": 0.3}])
