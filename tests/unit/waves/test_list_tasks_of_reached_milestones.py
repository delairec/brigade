import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.waves.list_tasks_of_reached_milestones import TaskOfAReachedMilestone, list_tasks_of_reached_milestones
from brigade.waves.read_project_tasks import ProjectTasks
from tests.unit.scripted_processes import ScriptedProcesses

ROOT = Path("/cache/refs/shop/4f1c2a9")
REACHED_MILESTONES = ("awawa", "status", "MILESTONE", "--where", "STATUS==reached", "--json", str(ROOT))
NO_TASK_IMPLEMENTED = frozenset()
READ_AT_MAIN = None
S1_TODO_OF_M9 = Entity(
    name="S1", fields=(EntityField(name="STATUS", value="todo"), EntityField(name="MILESTONE", value="@MILESTONE.M9"))
)
S2_DRAFT_OF_M9 = Entity(
    name="S2", fields=(EntityField(name="STATUS", value="draft"), EntityField(name="MILESTONE", value="@MILESTONE.M9"))
)
S3_IMPLEMENTED_OF_M9 = Entity(
    name="S3",
    fields=(EntityField(name="STATUS", value="implemented"), EntityField(name="MILESTONE", value="@MILESTONE.M9")),
)
S4_TODO_OF_M10 = Entity(
    name="S4", fields=(EntityField(name="STATUS", value="todo"), EntityField(name="MILESTONE", value="@MILESTONE.M10"))
)
S5_TODO_NAMING_NO_MILESTONE = Entity(name="S5", fields=(EntityField(name="STATUS", value="todo"),))


class ListTasksOfReachedMilestonesTest(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()
        self.processes.answer_json(REACHED_MILESTONES, {"entities": [{"type": "MILESTONE", "name": "M9"}]})

    def test_should_list_the_draft_and_todo_tasks_naming_a_reached_milestone(self):
        # Arrange
        main = ProjectTasks(
            root=ROOT,
            by_name={"S1": S1_TODO_OF_M9, "S2": S2_DRAFT_OF_M9, "S3": S3_IMPLEMENTED_OF_M9, "S4": S4_TODO_OF_M10},
            implemented=NO_TASK_IMPLEMENTED,
            milestone=READ_AT_MAIN,
        )

        # Act
        held = list_tasks_of_reached_milestones(self.processes, main)

        # Assert
        self.assertEqual(
            held,
            (
                TaskOfAReachedMilestone(task="S1", milestone="@MILESTONE.M9"),
                TaskOfAReachedMilestone(task="S2", milestone="@MILESTONE.M9"),
            ),
        )

    def test_should_read_no_milestone_when_no_draft_or_todo_task_names_one(self):
        # Arrange
        main = ProjectTasks(
            root=ROOT,
            by_name={"S3": S3_IMPLEMENTED_OF_M9, "S5": S5_TODO_NAMING_NO_MILESTONE},
            implemented=NO_TASK_IMPLEMENTED,
            milestone=READ_AT_MAIN,
        )

        # Act
        list_tasks_of_reached_milestones(self.processes, main)

        # Assert
        self.assertEqual(self.processes.list_argvs(), [])
