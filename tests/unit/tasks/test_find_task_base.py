import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.tasks.find_task_base import find_task_base
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

TIDEPOOL = Entity(name="tidepool", fields=(EntityField(name="MAIN", value="trunk"),))
WORKTREE = Path("/srv/tidepool-T7")
TIDES_BRANCH_CUT = {
    "schema_version": 1,
    "ts": "2026-09-29T22:00:00Z",
    "event": "milestone.branch_cut",
    "project": "tidepool",
    "milestone": "M4",
    "branch": "integration/tides",
    "login": None,
}
TASK_OF_THE_MILESTONE = (("MILESTONE", "@MILESTONE.M4"),)
TASK_OF_NO_MILESTONE = ()


class FindTaskBaseTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)

    def test_should_take_the_branch_of_its_milestone_as_the_base_of_a_task(self):
        # Arrange
        write_ledger(self.root, [TIDES_BRANCH_CUT])
        self.processes.answer_entity(WORKTREE, "TASK", "T7", TASK_OF_THE_MILESTONE)

        # Act
        base = find_task_base(self.runtime, WORKTREE, TIDEPOOL, "T7")

        # Assert
        self.assertEqual(base, "integration/tides")

    def test_should_take_the_main_branch_of_the_project_as_the_base_of_a_task_naming_no_milestone(self):
        # Arrange
        self.processes.answer_entity(WORKTREE, "TASK", "T7", TASK_OF_NO_MILESTONE)

        # Act
        base = find_task_base(self.runtime, WORKTREE, TIDEPOOL, "T7")

        # Assert
        self.assertEqual(base, "trunk")

    def test_should_refuse_a_task_whose_milestone_has_no_branch(self):
        # Arrange
        self.processes.answer_entity(WORKTREE, "TASK", "T7", TASK_OF_THE_MILESTONE)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            find_task_base(self.runtime, WORKTREE, TIDEPOOL, "T7")

        # Assert
        self.assertEqual(str(refusal.exception), "@MILESTONE.M4 of @TASK.T7 has no branch in the ledger")
