import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands._launch_branch_rebase import launch_branch_rebase
from brigade.system.parse_configuration import Configuration
from brigade.waves.rebase_milestone_branches import BranchRebaseRun
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class LaunchBranchRebaseTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        self.repository = self.root / "shop"
        self.worktree = self.repository / ".brigade" / "worktrees" / "integration-shop_w1"
        self.worktree.mkdir(parents=True)
        corpus = {"PROJECT": {"shop": (("PATH", str(self.repository)),)}}
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_corpus_double(corpus),
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

    def read_record(self) -> dict:
        (record,) = (self.root / "state" / "runs").glob("*/run.json")
        return json.loads(record.read_text(encoding="utf-8"))

    def test_should_start_a_run_of_the_rebase_slot_on_the_worktree_of_the_branch_with_its_base_and_no_task(self):
        # Arrange
        rebase = BranchRebaseRun(
            project="shop",
            worktree=self.worktree,
            branch="integration/shop_w1",
            base="integration/dashboard",
            wave="shop_w1",
        )

        # Act
        launch_branch_rebase(self.runtime, Configuration(), rebase)

        # Assert
        record = self.read_record()
        self.assertEqual(record["procedure"], "rebase-on-base")
        self.assertEqual(record["slot"], "rebase")
        self.assertEqual(record["cwd"], str(self.worktree))
        self.assertEqual(record["arguments"], {"base": "integration/dashboard"})
        self.assertEqual(record["wave"], "shop_w1")
        self.assertIsNone(record["task"])
