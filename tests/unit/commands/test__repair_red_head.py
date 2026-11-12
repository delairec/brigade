import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands._repair_red_head import repair_red_head
from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRecord
from brigade.tick.head_proof import HeadProof, HoldingHead
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

RED_HEAD = "8885daa"
RED_MILESTONE_BRANCH = HoldingHead(
    branch="integration/shop_w1",
    proof=HeadProof(commit=RED_HEAD, state="red", failed_commands=("make test",)),
)


class RepairRedHeadTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        self.repository = self.root / "shop"
        self.worktree = self.repository / ".brigade" / "worktrees" / "integration-shop_w1"
        self.project = Entity(
            name="shop",
            fields=(EntityField(name="PATH", value=str(self.repository)), EntityField(name="MAIN", value="main")),
        )
        self.argvs = []
        corpus_double = create_corpus_double({"PROJECT": {"shop": (("PATH", str(self.repository)),)}})

        def run_process(request):
            self.argvs.append(request.argv)
            if request.argv[:3] == ("git", "worktree", "add"):
                Path(request.argv[-2]).mkdir(parents=True, exist_ok=True)
                return ProcessRecord(
                    argv=request.argv, cwd=request.cwd, exit_code=0, stdout="", stderr="", duration_ms=0
                )
            return corpus_double(request)

        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=run_process,
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

    def _list_runs(self) -> list:
        return sorted((self.root / "state" / "runs").glob("*/run.json"))

    def test_should_launch_no_repair_of_a_head_whose_checks_are_pending(self):
        # Arrange
        pending = HoldingHead(
            branch="integration/shop_w1", proof=HeadProof(commit=RED_HEAD, state="pending", failed_commands=())
        )

        # Act
        repair_red_head(self.runtime, Configuration(), self.project, pending)

        # Assert
        self.assertEqual(self._list_runs(), [])

    def test_should_open_the_worktree_of_the_red_milestone_branch_on_that_branch(self):
        # Act
        repair_red_head(self.runtime, Configuration(), self.project, RED_MILESTONE_BRANCH)

        # Assert
        self.assertIn(("git", "worktree", "add", "--quiet", str(self.worktree), "integration/shop_w1"), self.argvs)

    def test_should_repair_in_the_existing_worktree_of_the_red_milestone_branch_without_adding_it(self):
        # Arrange
        self.worktree.mkdir(parents=True)

        # Act
        repair_red_head(self.runtime, Configuration(), self.project, RED_MILESTONE_BRANCH)

        # Assert
        (record,) = self._list_runs()
        self.assertNotIn(("git", "worktree", "add", "--quiet", str(self.worktree), "integration/shop_w1"), self.argvs)
        self.assertEqual(json.loads(record.read_text())["cwd"], str(self.worktree))
