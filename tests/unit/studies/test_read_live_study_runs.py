import json
import tempfile
import unittest
from pathlib import Path

from brigade.studies.read_live_study_runs import LiveStudyRun, read_live_study_runs


class ReadLiveStudyRunsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state_root = Path(directory.name)

    def create_order_run(self, run: str, order: str, recipe: str) -> Path:
        run_directory = self.state_root / "runs" / run
        run_directory.mkdir(parents=True)
        (run_directory / "order.json").write_text(
            json.dumps({"order": {"name": order}, "recipe": {"name": recipe}}), encoding="utf-8"
        )
        return run_directory

    def test_should_read_the_study_runs_whose_process_is_alive(self):
        # Arrange
        live_run = self.create_order_run("r1", "trees", "study")
        self.create_order_run("r2", "ash", "study")
        is_alive = {live_run}.__contains__

        # Act
        live = read_live_study_runs(self.state_root, is_alive)

        # Assert
        self.assertEqual(live, (LiveStudyRun(study="trees", run="r1"),))

    def test_should_leave_out_a_live_run_of_an_order_of_another_recipe(self):
        # Arrange
        live_run = self.create_order_run("r1", "nightly", "usage-report")
        is_alive = {live_run}.__contains__

        # Act
        live = read_live_study_runs(self.state_root, is_alive)

        # Assert
        self.assertEqual(live, ())

    def test_should_present_a_live_study_run_by_its_study_and_run(self):
        # Arrange
        live = LiveStudyRun(study="trees", run="r1")

        # Act
        document = live.to_document()

        # Assert
        self.assertEqual(document, {"study": "trees", "run": "r1"})
