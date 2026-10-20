import tempfile
import unittest
from pathlib import Path

from brigade.verify.read_review_mode import read_review_mode
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadReviewModeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)

    def test_should_read_the_review_mode_the_policy_of_the_project_sets(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "POLICY",
            {
                "elm_review": (("PROJECT", "@PROJECT.elm"), ("REVIEW", "local")),
                "oak_review": (("PROJECT", "@PROJECT.oak"), ("REVIEW", "approval")),
            },
        )

        # Act
        mode = read_review_mode(self.runtime, "oak")

        # Assert
        self.assertEqual(mode, "approval")

    def test_should_review_by_verdict_when_no_policy_of_the_project_sets_a_mode(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "POLICY",
            {
                "elm_review": (("PROJECT", "@PROJECT.elm"), ("REVIEW", "approval")),
                "oak_review": (("PROJECT", "@PROJECT.oak"), ("PLAN_REVIEW", "ask")),
            },
        )

        # Act
        mode = read_review_mode(self.runtime, "oak")

        # Assert
        self.assertEqual(mode, "verdict")
