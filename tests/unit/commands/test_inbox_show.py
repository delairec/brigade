import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.inbox_show import COMMAND, inbox_show
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_RECORDED
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


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
