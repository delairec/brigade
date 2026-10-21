import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands._launch_planner import launch_planner
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    CLOCK_PROBE,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)


class LaunchPlannerTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        self.repository = self.root / "shop"
        self.repository.mkdir()

    def _create_runtime(self, probe: dict):
        corpus = {"PROJECT": {"shop": (("PATH", str(self.repository)),)}}
        return create_runtime(
            self.root,
            run_process=create_corpus_double(corpus),
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(probe),
        )

    def test_should_start_the_planner_of_the_request_detached(self):
        # Arrange
        runtime = self._create_runtime(STEP_COUNTING_PROBE)

        # Act
        launched = launch_planner(runtime, "shop", "shop_r2")

        # Assert
        record = json.loads((self.root / "state" / "runs" / launched["run"] / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(
            (record["procedure"], record["slot"], record["project"], record["arguments"]),
            ("wave-plan", "plan", "shop", {"request": "shop_r2"}),
        )

    def test_should_carry_the_warning_of_the_planner_run(self):
        # Arrange
        runtime = self._create_runtime(CLOCK_PROBE)

        # Act
        launched = launch_planner(runtime, "shop", "shop_r2")

        # Assert
        self.assertEqual(
            launched["warnings"],
            [
                "double counts no steps: the budget of 30 steps is held on the clock and the run cut at its limit of 1140 s"
            ],
        )


if __name__ == "__main__":
    unittest.main()
