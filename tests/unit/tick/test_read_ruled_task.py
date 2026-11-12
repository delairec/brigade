import tempfile
import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.system.parse_configuration import Configuration
from brigade.tick.actions import LaunchTask
from brigade.tick.prepare_task_worktree import PreparedWorktree
from brigade.tick.read_ruled_task import read_ruled_task
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

SHA = "c0ffee"


class ReadRuledTaskTest(unittest.TestCase):
    def test_should_read_the_task_in_the_area_of_the_worktree(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_operational_corpus(root)
        processes = ScriptedProcesses()
        runtime = create_test_runtime(create_test_paths(root), run_process=processes)
        processes.answer_entities(
            runtime.paths.config_root,
            "PROJECT",
            {"oak": (("PATH", "/srv/oak"), ("CORPUS", "brigade"), ("MODE", "area"))},
        )
        processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "integration/w1^{commit}"),
            stdout=f"{SHA}\n",
        )
        tree = root / "cache" / "refs" / "oak" / SHA / "brigade"
        tree.mkdir(parents=True)
        worktree = Path("/srv/oak-b12")
        processes.answer_entity(tree, "TASK", "B12", (("STATUS", "todo"),))
        processes.answer_entity(worktree / "brigade", "TASK", "B12", (("STATUS", "draft"),))
        action = LaunchTask(
            project="oak",
            wave="oak_w1",
            branch="integration/w1",
            task="B12",
            task_branch="feature/B12-the-parser",
            pull_request_checks=None,
        )
        prepared = PreparedWorktree(
            worktree=BranchWorktree(path=worktree, branch="feature/B12-the-parser", start="integration/w1"),
            conflicted=False,
            on_start=False,
        )

        # Act
        ruled = read_ruled_task(runtime, Configuration(), action, prepared)

        # Assert
        self.assertEqual(ruled.name, "B12")
