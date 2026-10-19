import tempfile
import unittest
from pathlib import Path

from brigade.waves.decide_waits_for import decide_waits_for
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class DecideWaitsForTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)

    def test_should_wait_for_nothing_while_the_request_is_not_planned(self):
        # Act
        waits_for = decide_waits_for(self.runtime, {"status": "running", "project": "oak"})

        # Assert
        self.assertIsNone(waits_for)

    def test_should_wait_for_the_start_of_the_wave_when_the_project_reviews_its_plans(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "POLICY",
            {"oak_review": (("PROJECT", "@PROJECT.oak"), ("PLAN_REVIEW", "ask"))},
        )

        # Act
        waits_for = decide_waits_for(self.runtime, {"status": "planned", "project": "oak"})

        # Assert
        self.assertEqual(waits_for, "brigade wave start")

    def test_should_wait_for_the_next_tick_when_the_plan_needs_no_review(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "POLICY",
            {
                "elm_review": (("PROJECT", "@PROJECT.elm"), ("PLAN_REVIEW", "ask")),
                "oak_review": (("PROJECT", "@PROJECT.oak"), ("PLAN_REVIEW", "auto")),
            },
        )

        # Act
        waits_for = decide_waits_for(self.runtime, {"status": "planned", "project": "oak"})

        # Assert
        self.assertEqual(waits_for, "the next tick")
