import json
import tempfile
import unittest
from pathlib import Path

from brigade.runs.is_run_live_on import is_run_live_on

WORKTREE = Path("/srv/shop/.brigade/worktrees/integration-dashboard")
OTHER_WORKTREE = Path("/srv/shop/.brigade/worktrees/B27")


class IsRunLiveOnTest(unittest.TestCase):
    def setUp(self):
        self.state_root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.live_runs: set[str] = set()

    def write_run(self, run: str, cwd: Path) -> None:
        directory = self.state_root / "runs" / run
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"run": run, "cwd": str(cwd)}), encoding="utf-8")

    def is_alive(self, run_directory: Path) -> bool:
        return run_directory.name in self.live_runs

    def test_should_find_a_live_run_in_the_worktree(self):
        # Arrange
        self.write_run("20261030T000001Z-2ec491", WORKTREE)
        self.live_runs = {"20261030T000001Z-2ec491"}

        # Act
        live = is_run_live_on(self.state_root, WORKTREE, self.is_alive)

        # Assert
        self.assertTrue(live)

    def test_should_find_none_when_the_run_of_the_worktree_ended(self):
        # Arrange
        self.write_run("20261030T000001Z-2ec491", WORKTREE)

        # Act
        live = is_run_live_on(self.state_root, WORKTREE, self.is_alive)

        # Assert
        self.assertFalse(live)

    def test_should_find_none_when_the_live_run_works_in_another_worktree(self):
        # Arrange
        self.write_run("20261030T000002Z-7a1b2c", OTHER_WORKTREE)
        self.live_runs = {"20261030T000002Z-7a1b2c"}

        # Act
        live = is_run_live_on(self.state_root, WORKTREE, self.is_alive)

        # Assert
        self.assertFalse(live)

    def test_should_find_none_before_any_run(self):
        # Act
        live = is_run_live_on(self.state_root, WORKTREE, self.is_alive)

        # Assert
        self.assertFalse(live)
