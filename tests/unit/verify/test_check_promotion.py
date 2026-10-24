import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.verify.check_promotion import PromotionFacts, check_promotion
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


def create_spec(text: str, anchor: str) -> dict:
    return {
        "name": "SPEC",
        "atoms": [json.dumps(text)],
        "fields": [{"name": "IMPL", "atoms": [json.dumps(anchor)], "fields": []}],
    }


class CheckPromotionTest(unittest.TestCase):
    def setUp(self):
        self.head_tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.head_tree)
        (self.head_tree / "brigade").mkdir()
        (self.head_tree / "brigade" / "cli.py").write_text("def main(arguments):\n")

    def check(self, fields: list[dict]) -> dict:
        awawa = RecordingProcessRunner(
            {
                ("awawa", "show", "@TASK.B1", "--json", str(self.head_tree)): ProcessAnswer(
                    stdout=json.dumps({"fields": fields})
                )
            }
        )
        return check_promotion(awawa, PromotionFacts(head_tree=self.head_tree, task="B1", pr=160))

    def test_should_pass_a_task_implemented_delivered_by_the_pull_request_and_anchored(self):
        # Act
        check = self.check(
            [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {"name": "DELIVERED_BY", "atoms": ['"160"'], "fields": []},
                create_spec("runs the command line", "brigade/cli.py::def main"),
            ]
        )

        # Assert
        self.assertEqual(check, {"name": "promotion", "verdict": "pass", "findings": []})

    def test_should_fail_a_task_left_unpromoted_and_unanchored(self):
        # Act
        check = self.check(
            [
                {"name": "STATUS", "atoms": ["todo"], "fields": []},
                create_spec("runs the command line", "brigade/cli.py::def launch"),
                create_spec("ships a launcher", "brigade/launcher.py::def launch"),
            ]
        )

        # Assert
        self.assertEqual(
            check,
            {
                "name": "promotion",
                "verdict": "fail",
                "findings": [
                    "@TASK.B1 is STATUS todo, not implemented",
                    "@TASK.B1 is delivered by no pull request, not by #160",
                    "SPEC 1 has no IMPL whose anchor resolves: runs the command line",
                    "SPEC 2 has no IMPL whose anchor resolves: ships a launcher",
                ],
            },
        )

    def test_should_fail_a_task_delivered_by_another_pull_request(self):
        # Act
        check = self.check(
            [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {"name": "DELIVERED_BY", "atoms": ["158"], "fields": []},
            ]
        )

        # Assert
        self.assertEqual(check["findings"], ["@TASK.B1 is delivered by #158, not by #160"])

    def test_should_name_an_unanchored_criterion_with_the_backslash_awawa_keeps(self):
        # Act
        check = self.check(
            [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {"name": "DELIVERED_BY", "atoms": ["160"], "fields": []},
                {"name": "SPEC", "atoms": [r'"matches brigade/cli\.py"'], "fields": []},
            ]
        )

        # Assert
        self.assertEqual(
            check,
            {
                "name": "promotion",
                "verdict": "fail",
                "findings": [r"SPEC 1 has no IMPL whose anchor resolves: matches brigade/cli\.py"],
            },
        )
