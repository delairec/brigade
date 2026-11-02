import json
import re
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.transcripts import collect
from brigade.ledger.append_event import append_event
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.run_finished import RunFinished
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.mining.create_run_finished import create_run_finished
from tests.unit.mining.transcripts_client_double import TranscriptsClientDouble
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


class TranscriptsCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), now=NOW, run_process=self.processes)
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

    def finish(self, instant: datetime, finished: RunFinished, worktree: str) -> None:
        run_directory = self.runtime.paths.state_root / "runs" / finished.run
        run_directory.mkdir(parents=True)
        (run_directory / "run.json").write_text(json.dumps({"run": finished.run, "worktree": worktree}))
        append_event(self.runtime.paths, instant, finished)

    def collect(self, client: TranscriptsClientDouble) -> dict:
        equipment = CollectorEquipment(
            configuration=Configuration(), forge=None, forge_name="github", resolve_client=lambda name: client
        )
        return collect(ENVIRONMENT, self.runtime, equipment)

    def test_should_print_the_messages_of_each_session_a_run_finished_names_in_the_window(self):
        # Arrange
        self.finish(BEFORE_THE_WINDOW, create_run_finished("r1", "s-before"), "/srv/oak/.brigade/worktrees/B41")
        self.finish(IN_THE_WINDOW, create_run_finished("r2", None), "/srv/oak/.brigade/worktrees/B42")
        append_event(
            self.runtime.paths, IN_THE_WINDOW, OrderStarted(project="oak", kind="study", order="trees", run="r0")
        )
        self.finish(IN_THE_WINDOW, create_run_finished("r3", "s-built"), "/srv/oak/.brigade/worktrees/B42")
        client = TranscriptsClientDouble({"s-before": [BRIEF], "s-built": [BRIEF, ANSWER]})

        # Act
        document = self.collect(client)

        # Assert
        identity = {"client": "vibe", "session": "s-built", "run": "r3", "project": "oak", "task": "B42"}
        self.assertEqual(
            document["items"],
            [{**identity, "position": 1, **BRIEF}, {**identity, "position": 2, **ANSWER}],
        )
        self.assertEqual(client.worktrees, ["/srv/oak/.brigade/worktrees/B42"])

    def test_should_list_a_session_whose_transcript_cannot_be_read_with_its_run_and_the_reason(self):
        # Arrange
        self.finish(IN_THE_WINDOW, create_run_finished("r3", "s-lost"), "/srv/oak/.brigade/worktrees/B42")
        self.finish(IN_THE_WINDOW, create_run_finished("r4", "s-built"), "/srv/oak/.brigade/worktrees/B43")
        client = TranscriptsClientDouble({"s-built": [BRIEF]})

        # Act
        document = self.collect(client)

        # Assert
        self.assertEqual(
            document["summary"],
            {
                "sessions": 1,
                "messages": 1,
                "unreadable": [
                    {"run": "r3", "session": "s-lost", "reason": "client adapter vibe: no transcript of session s-lost"}
                ],
            },
        )

    def test_should_list_a_session_whose_run_directory_was_pruned_with_its_run_and_the_reason(self):
        # Arrange
        append_event(self.runtime.paths, IN_THE_WINDOW, create_run_finished("r2", "s-pruned"))
        self.finish(IN_THE_WINDOW, create_run_finished("r4", "s-built"), "/srv/oak/.brigade/worktrees/B43")
        client = TranscriptsClientDouble({"s-pruned": [BRIEF], "s-built": [BRIEF]})

        # Act
        document = self.collect(client)

        # Assert
        self.assertEqual(
            document["summary"],
            {
                "sessions": 1,
                "messages": 1,
                "unreadable": [
                    {"run": "r2", "session": "s-pruned", "reason": "run r2: no run record, its directory was pruned"}
                ],
            },
        )

    def test_should_declare_its_document_not_cached(self):
        # Arrange
        no_transcripts = {}

        # Act
        document = self.collect(TranscriptsClientDouble(no_transcripts))

        # Assert
        self.assertIs(document["cache"], NOT_CACHED)

    def test_should_leave_no_identifier_a_private_pattern_or_a_built_in_matches(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("PRIVATE", r"Acme\w*"))}
        )
        self.finish(IN_THE_WINDOW, create_run_finished("r3", "s-lost"), "/home/alice/oak/.brigade/worktrees/B42")
        self.finish(IN_THE_WINDOW, create_run_finished("r4", "s-built"), "/home/alice/oak/.brigade/worktrees/B43")
        leaking_brief = {**BRIEF, "content": "Mail ada@example.org the AcmeBilling report from /home/alice/oak."}
        client = TranscriptsClientDouble({"s-built": [leaking_brief]})

        # Act
        document = self.collect(client)

        # Assert
        printed = json.dumps(document)
        self.assertNotRegex(printed, re.compile(r"Acme\w*"))
        self.assertNotRegex(printed, re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"))
        self.assertNotRegex(printed, re.compile(r"/(?:home|Users)/[\w.-]+"))
