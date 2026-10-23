import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.tasks.locate_task_worktree import TaskWorktree, locate_task_worktree
from tests.unit.commands.command_runtime import write_ledger, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

OAK_WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-10-19T08:00:00Z",
    "event": "wave.started",
    "wave": "oak_w1",
    "project": "oak",
    "branch": "integration/oak_w1",
    "tasks": ["B12"],
}


class LocateTaskWorktreeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.root = Path(directory.name)
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.config_root = self.runtime.paths.config_root
        self.processes.answer(("git", "rev-parse", "--show-toplevel"), stdout="/srv/oak-b12\n")

    def check_out(self, branch: str) -> None:
        self.processes.answer(("git", "branch", "--show-current"), stdout=f"{branch}\n")
        self.processes.answer(
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"), stdout="/srv/oak/.git\n"
        )
        self.processes.answer_entities(self.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

    def test_should_locate_the_task_its_project_and_its_wave_from_the_branch_of_the_worktree(self):
        # Arrange
        self.check_out("task/oak_w1/B12")
        write_ledger(self.root, [OAK_WAVE_STARTED])

        # Act
        worktree = locate_task_worktree(self.runtime, Path("/srv/oak-b12/src"), None)

        # Assert
        self.assertEqual(
            worktree,
            TaskWorktree(
                path=Path("/srv/oak-b12"),
                task="B12",
                project=Entity(name="oak", fields=(EntityField(name="PATH", value="/srv/oak"),)),
                wave="oak_w1",
                wave_branch="integration/oak_w1",
            ),
        )

    def test_should_refuse_a_branch_that_is_not_a_task_branch(self):
        # Arrange
        self.check_out("main")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            locate_task_worktree(self.runtime, Path("/srv/oak-b12"), None)

        # Assert
        self.assertEqual(str(refusal.exception), "the branch main is not a task/<slug>/<task> branch")

    def test_should_refuse_a_task_other_than_the_task_of_the_branch(self):
        # Arrange
        self.check_out("task/oak_w1/B12")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            locate_task_worktree(self.runtime, Path("/srv/oak-b12"), "B13")

        # Assert
        self.assertEqual(str(refusal.exception), "@TASK.B13 is not the task of the branch task/oak_w1/B12")

    def test_should_refuse_a_task_branch_no_wave_of_the_project_started(self):
        # Arrange
        self.check_out("task/oak_w1/B12")
        write_ledger(self.root, [{**OAK_WAVE_STARTED, "project": "elm"}])

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            locate_task_worktree(self.runtime, Path("/srv/oak-b12"), "B12")

        # Assert
        self.assertEqual(str(refusal.exception), "no wave.started of @PROJECT.oak has the branch integration/oak_w1")
