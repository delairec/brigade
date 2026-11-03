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
    "tasks": ["B12"],
}
OAK_MILESTONE_BRANCH_CUT = {
    "schema_version": 1,
    "ts": "2026-10-19T07:00:00Z",
    "event": "milestone.branch_cut",
    "project": "oak",
    "milestone": "M2",
    "branch": "integration/harvest",
    "login": None,
}
OAK_WAVE_CLOSED = {"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "wave.closed", "wave": "oak_w1"}
TASK_BRANCH = "feature/B12-plant-the-oak"
TASK_IN_MILESTONE = (("MILESTONE", "@MILESTONE.M2"),)
TASK_IN_NO_MILESTONE = ()


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

    def check_out(self, branch: str, task_fields: tuple[tuple[str, str], ...] = TASK_IN_MILESTONE) -> None:
        self.processes.answer(("git", "branch", "--show-current"), stdout=f"{branch}\n")
        self.processes.answer(
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"), stdout="/srv/oak/.git\n"
        )
        self.processes.answer_entities(self.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("MAIN", "trunk"))})
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", task_fields)

    def test_should_locate_the_task_its_project_its_wave_and_its_milestone_branch_from_the_branch(self):
        # Arrange
        self.check_out(TASK_BRANCH)
        write_ledger(self.root, [OAK_MILESTONE_BRANCH_CUT, OAK_WAVE_STARTED])

        # Act
        worktree = locate_task_worktree(self.runtime, Path("/srv/oak-b12/src"), None)

        # Assert
        self.assertEqual(
            worktree,
            TaskWorktree(
                path=Path("/srv/oak-b12"),
                task="B12",
                project=Entity(
                    name="oak",
                    fields=(EntityField(name="PATH", value="/srv/oak"), EntityField(name="MAIN", value="trunk")),
                ),
                wave="oak_w1",
                base="integration/harvest",
            ),
        )

    def test_should_take_the_main_branch_of_the_project_as_the_base_of_a_task_naming_no_milestone(self):
        # Arrange
        self.check_out(TASK_BRANCH, TASK_IN_NO_MILESTONE)
        write_ledger(self.root, [OAK_WAVE_STARTED])

        # Act
        worktree = locate_task_worktree(self.runtime, Path("/srv/oak-b12"), None)

        # Assert
        self.assertEqual(worktree.base, "trunk")

    def test_should_read_the_task_of_a_branch_whose_slug_is_empty(self):
        # Arrange
        self.check_out("fix/B12-", TASK_IN_NO_MILESTONE)
        write_ledger(self.root, [OAK_WAVE_STARTED])

        # Act
        worktree = locate_task_worktree(self.runtime, Path("/srv/oak-b12"), None)

        # Assert
        self.assertEqual(worktree.task, "B12")

    def test_should_accept_the_task_of_the_branch_named_as_its_argument(self):
        # Arrange
        self.check_out(TASK_BRANCH)
        write_ledger(self.root, [OAK_MILESTONE_BRANCH_CUT, OAK_WAVE_STARTED])

        # Act
        worktree = locate_task_worktree(self.runtime, Path("/srv/oak-b12"), "B12")

        # Assert
        self.assertEqual(worktree.task, "B12")

    def test_should_read_the_task_of_a_branch_of_every_prefix_a_task_type_gives(self):
        for prefix in ("build", "chore", "ci", "docs", "feature", "fix", "perf", "refactor", "revert", "style", "test"):
            with self.subTest(prefix=prefix):
                # Arrange
                self.check_out(f"{prefix}/B12-plant-the-oak", TASK_IN_NO_MILESTONE)
                write_ledger(self.root, [OAK_WAVE_STARTED])

                # Act
                worktree = locate_task_worktree(self.runtime, Path("/srv/oak-b12"), None)

                # Assert
                self.assertEqual(worktree.task, "B12")

    def test_should_refuse_a_branch_that_is_not_a_task_branch(self):
        for branch in ("main", "integration/plant-the-oak", "feat/B12-plant-the-oak"):
            with self.subTest(branch=branch):
                # Arrange
                self.check_out(branch)

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    locate_task_worktree(self.runtime, Path("/srv/oak-b12"), None)

                # Assert
                self.assertEqual(str(refusal.exception), f"the branch {branch} is not a <prefix>/<task>-<slug> branch")

    def test_should_refuse_a_task_other_than_the_task_of_the_branch(self):
        # Arrange
        self.check_out(TASK_BRANCH)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            locate_task_worktree(self.runtime, Path("/srv/oak-b12"), "B13")

        # Assert
        self.assertEqual(str(refusal.exception), "@TASK.B13 is not the task of the branch feature/B12-plant-the-oak")

    def test_should_refuse_a_task_no_open_wave_of_the_project_holds(self):
        # Arrange
        self.check_out(TASK_BRANCH)
        write_ledger(self.root, [OAK_MILESTONE_BRANCH_CUT, OAK_WAVE_STARTED, OAK_WAVE_CLOSED])

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            locate_task_worktree(self.runtime, Path("/srv/oak-b12"), "B12")

        # Assert
        self.assertEqual(str(refusal.exception), "no open wave of @PROJECT.oak holds @TASK.B12")

    def test_should_refuse_a_task_whose_milestone_has_no_branch(self):
        # Arrange
        self.check_out(TASK_BRANCH)
        write_ledger(self.root, [OAK_WAVE_STARTED])

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            locate_task_worktree(self.runtime, Path("/srv/oak-b12"), "B12")

        # Assert
        self.assertEqual(str(refusal.exception), "@MILESTONE.M2 of @TASK.B12 has no branch in the ledger")
