import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.ledger.task_branch_cut import TaskBranchCut
from brigade.tick.read_branch_of_task import read_branch_of_task

RETITLED_TASK = Entity(
    name="B46",
    fields=(
        EntityField(name="TITLE", value="A project of forge none acts through no forge"),
        EntityField(name="TYPE", value="feat"),
    ),
)
RETYPED_TASK = Entity(
    name="B46",
    fields=(
        EntityField(name="TITLE", value="A project of forge none runs its waves"),
        EntityField(name="TYPE", value="fix"),
    ),
)
FIRST_CUT = TaskBranchCut(project="brigade", task="B46", branch="feature/B46-a-project-of-forge-none-runs-its-waves")


class ReadBranchOfACutTaskTest(unittest.TestCase):
    def test_should_keep_the_first_branch_of_a_task_whose_title_changed_since_its_cut(self):
        # Arrange
        events = (FIRST_CUT,)

        # Act
        branch = read_branch_of_task(events, "brigade", RETITLED_TASK)

        # Assert
        self.assertEqual(branch, "feature/B46-a-project-of-forge-none-runs-its-waves")

    def test_should_keep_the_first_branch_of_a_task_whose_type_changed_since_its_cut(self):
        # Arrange
        events = (FIRST_CUT,)

        # Act
        branch = read_branch_of_task(events, "brigade", RETYPED_TASK)

        # Assert
        self.assertEqual(branch, "feature/B46-a-project-of-forge-none-runs-its-waves")

    def test_should_read_the_branch_of_the_last_cut_of_the_task(self):
        # Arrange
        events = (
            FIRST_CUT,
            TaskBranchCut(project="brigade", task="B46", branch="feature/B46-cut-again-after-a-removal"),
        )

        # Act
        branch = read_branch_of_task(events, "brigade", RETITLED_TASK)

        # Assert
        self.assertEqual(branch, "feature/B46-cut-again-after-a-removal")


class ReadBranchOfAnUncutTaskTest(unittest.TestCase):
    def test_should_name_a_task_with_no_cut_from_its_type_and_its_title(self):
        # Arrange
        no_event = ()

        # Act
        branch = read_branch_of_task(no_event, "brigade", RETITLED_TASK)

        # Assert
        self.assertEqual(branch, "feature/B46-a-project-of-forge-none-acts-through-no")

    def test_should_name_a_task_from_its_type_and_its_title_past_the_cut_of_a_task_of_another_project(self):
        # Arrange
        events = (TaskBranchCut(project="shop", task="B46", branch="feature/B46-empty-the-cart"),)

        # Act
        branch = read_branch_of_task(events, "brigade", RETITLED_TASK)

        # Assert
        self.assertEqual(branch, "feature/B46-a-project-of-forge-none-acts-through-no")

    def test_should_name_a_task_from_its_type_and_its_title_past_the_cut_of_another_task(self):
        # Arrange
        events = (TaskBranchCut(project="brigade", task="B47", branch="feature/B47-stop-a-run"),)

        # Act
        branch = read_branch_of_task(events, "brigade", RETITLED_TASK)

        # Assert
        self.assertEqual(branch, "feature/B46-a-project-of-forge-none-acts-through-no")
