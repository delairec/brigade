import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.inbox_show import COMMAND, inbox_show
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_RECORDED
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.reports.document_plugin_double import DocumentPluginDouble
from tests.unit.scripted_processes import ScriptedProcesses


class InboxShowTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))
        signals = self.runtime.paths.state_root / "inbox" / "signals.jsonl"
        signals.parent.mkdir(parents=True)
        signals.write_text(NOTE_ON_OAK_RECORDED + THREAD_RECORDED, encoding="utf-8")

    def test_should_present_the_signal_with_its_evidence(self):
        # Arrange
        request = argparse.Namespace(id="1975")

        # Act
        document = inbox_show(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "signal": {
                    "id": "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                    "fingerprint": "rt:PRRT_kwDO",
                    "kind": "review_thread",
                    "project": None,
                    "count": 1,
                    "age_s": 3600,
                    "status": "new",
                    "evidence": {"pr": 12, "comment": "rename it"},
                },
            },
        )


class InboxShowTextTest(unittest.TestCase):
    def test_should_print_the_fields_of_the_signal_then_its_evidence(self):
        # Arrange
        document = {
            "schema_version": 1,
            "signal": {
                "id": "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                "fingerprint": "rt:PRRT_kwDO",
                "kind": "review_thread",
                "project": None,
                "count": 1,
                "age_s": 3600,
                "status": "new",
                "evidence": {"pr": 12, "line": None, "comment": "rename it"},
            },
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "id           19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f\n"
            "fingerprint  rt:PRRT_kwDO\n"
            "kind         review_thread\n"
            "project      -\n"
            "count        1\n"
            "age          1h\n"
            "status       new\n"
            "evidence\n"
            "  pr: 12\n"
            "  line: null\n"
            "  comment: rename it",
        )


class InboxShowOfAStudyAnswerTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "answers.awawa").write_text("", encoding="utf-8")
        answer = {
            "type": "ANSWER",
            "name": "disk_20261019T090000Z_b2",
            "fields": [{"name": "STUDY", "value": "disk"}, {"name": "SUMMARY", "value": "the disk is full"}],
        }
        plugin = DocumentPluginDouble({str(root / "config" / "answers.awawa"): [answer]})
        no_study = {}
        self.runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpus_double(no_study),
            resolve_plugin=create_plugin_resolver({("progress_form", "awawa"): plugin}),
        )

    def test_should_present_the_study_answer_the_id_names(self):
        # Arrange
        request = argparse.Namespace(id="disk_20261019T090000Z_b2")

        # Act
        document = inbox_show(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "answer": {
                    "id": "disk_20261019T090000Z_b2",
                    "study": "disk",
                    "project": None,
                    "type": "ANSWER",
                    "fields": [{"name": "STUDY", "value": "disk"}, {"name": "SUMMARY", "value": "the disk is full"}],
                },
            },
        )

    def test_should_print_the_study_answer_as_markdown(self):
        # Arrange
        document = {
            "schema_version": 1,
            "answer": {
                "id": "disk_20261019T090000Z_b2",
                "study": "disk",
                "project": None,
                "type": "ANSWER",
                "fields": [{"name": "SUMMARY", "value": "the disk is full"}],
            },
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "# ANSWER disk_20261019T090000Z_b2\n\n- SUMMARY: the disk is full\n")


class InboxShowOfAProposedPatternTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(root), run_process=processes)
        processes.answer_entities(
            self.runtime.paths.config_root,
            "PATTERN",
            {
                "FlakyTests": (
                    ("TITLE", "the tests are flaky"),
                    ("STATUS", "new"),
                    ("EVIDENCE", "note:474fa40ae4db fix the flaky test"),
                    ("EVIDENCE", "rt:PRRT_kwDO"),
                    ("ACTION", "constraint"),
                    ("TARGET", "tests/unit"),
                ),
                "Ratified": (("TITLE", "already ratified"), ("STATUS", "ratified"), ("ACTION", "wave")),
            },
        )

    def test_should_present_the_proposed_pattern_the_id_names_with_its_evidence(self):
        # Arrange
        request = argparse.Namespace(id="FlakyTests")

        # Act
        document = inbox_show(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "pattern": {
                    "name": "FlakyTests",
                    "title": "the tests are flaky",
                    "action": "constraint",
                    "target": "tests/unit",
                    "evidence": ["note:474fa40ae4db fix the flaky test", "rt:PRRT_kwDO"],
                },
            },
        )

    def test_should_refuse_a_pattern_that_is_no_longer_proposed(self):
        # Arrange
        request = argparse.Namespace(id="Ratified")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            inbox_show(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "no signal of the inbox has an id starting with Ratified")


class InboxShowTextOfAPatternTest(unittest.TestCase):
    def test_should_print_the_title_the_action_and_the_target_of_the_pattern_then_its_evidence(self):
        # Arrange
        no_target = None
        document = {
            "schema_version": 1,
            "pattern": {
                "name": "FlakyTests",
                "title": "the tests are flaky",
                "action": "constraint",
                "target": no_target,
                "evidence": ["note:474fa40ae4db fix the flaky test", "rt:PRRT_kwDO"],
            },
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "pattern      FlakyTests\n"
            "title        the tests are flaky\n"
            "action       constraint\n"
            "target       -\n"
            "evidence\n"
            "  note:474fa40ae4db fix the flaky test\n"
            "  rt:PRRT_kwDO",
        )
