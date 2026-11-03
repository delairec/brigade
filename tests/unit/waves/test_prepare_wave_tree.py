import json
import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.system.parse_configuration import Configuration
from brigade.waves.prepare_wave_tree import prepare_wave_tree
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

MILESTONE_SHA = "c0ffee1"
MAIN_SHA = "def456"
MILESTONE_BRANCH = "integration/tides"


def answer_tree(ref: str, sha: str) -> dict:
    argv = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")
    return {argv: ProcessAnswer(stdout=f"{sha}\n")}


def answer_tasks_of_m4(root: Path) -> dict:
    status = {"entities": [{"type": "TASK", "name": "B3"}]}
    return {
        ("awawa", "status", "TASK", "--where", "MILESTONE==@MILESTONE.M4", "--json", str(root)): ProcessAnswer(
            stdout=json.dumps(status)
        ),
        ("awawa", "show", "@TASK.B3", "--json", str(root)): ProcessAnswer(
            stdout=json.dumps({"fields": [{"name": "MILESTONE", "atoms": ["@MILESTONE.M4"]}]})
        ),
    }


class PrepareWaveTreeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.milestone_tree = self.paths.cache_root / "refs" / "shop" / MILESTONE_SHA
        self.milestone_tree.mkdir(parents=True)
        self.main_tree = self.paths.cache_root / "refs" / "shop" / MAIN_SHA
        self.main_tree.mkdir(parents=True)
        append_event(
            self.paths,
            FIXED_NOW - timedelta(minutes=60),
            MilestoneBranchCut(project="shop", milestone="M4", branch=MILESTONE_BRANCH, login="shop-cli"),
        )

    def prepare(self, started: WaveStarted) -> Path:
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(
                    self.paths.config_root, {"shop": {"PATH": str(self.root / "shop"), "MAIN": "main"}}
                ),
                **answer_tree(MILESTONE_BRANCH, MILESTONE_SHA),
                **answer_tree("main", MAIN_SHA),
                **answer_tasks_of_m4(self.milestone_tree),
            }
        )
        runtime = create_test_runtime(self.paths, run_process=runner)
        return prepare_wave_tree(runtime, Configuration(), started).root

    def test_should_read_the_tree_of_a_wave_at_the_branch_of_the_milestone_its_tasks_name(self):
        # Arrange
        started = WaveStarted(wave="shop_w2", project="shop", tasks=("B3",))

        # Act
        root = self.prepare(started)

        # Assert
        self.assertEqual(root, self.milestone_tree)

    def test_should_read_the_tree_of_a_wave_whose_tasks_name_no_milestone_at_the_main_branch(self):
        # Arrange
        started = WaveStarted(wave="shop_w3", project="shop", tasks=("B9",))

        # Act
        root = self.prepare(started)

        # Assert
        self.assertEqual(root, self.main_tree)

    def test_should_read_the_tree_of_a_wave_recorded_with_a_branch_at_the_branch_of_its_milestone(self):
        # Arrange
        started = WaveStarted(wave="shop_w1", project="shop", branch="integration/shop_w1", tasks=("B3",))

        # Act
        root = self.prepare(started)

        # Assert
        self.assertEqual(root, self.milestone_tree)

    def test_should_read_no_tree_at_the_branch_of_a_closed_milestone(self):
        # Arrange
        append_event(
            self.paths, FIXED_NOW - timedelta(minutes=30), MilestoneClosed(project="shop", milestone="M4", pr=90)
        )
        started = WaveStarted(wave="shop_w2", project="shop", tasks=("B3",))

        # Act
        root = self.prepare(started)

        # Assert
        self.assertEqual(root, self.main_tree)
