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


def create_task(name: str, *fields: tuple[str, str]) -> Entity:
    return Entity(name=name, fields=tuple(EntityField(name=field, value=value) for field, value in fields))


def create_main(*tasks: Entity) -> ProjectTasks:
    return ProjectTasks(
        root=ROOT,
        by_name={task.name: task for task in tasks},
        implemented=NO_TASK_IMPLEMENTED,
        milestone=READ_AT_MAIN,
    )


class ListTasksOfReachedMilestonesTest(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()
        self.processes.answer_json(REACHED_MILESTONES, {"entities": [{"type": "MILESTONE", "name": "M9"}]})

    def test_should_list_the_draft_and_todo_tasks_naming_a_reached_milestone(self):
        # Arrange
        main = create_main(
            create_task("S1", ("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9")),
            create_task("S2", ("STATUS", "draft"), ("MILESTONE", "@MILESTONE.M9")),
            create_task("S3", ("STATUS", "implemented"), ("MILESTONE", "@MILESTONE.M9")),
            create_task("S4", ("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M10")),
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
        main = create_main(
            create_task("S3", ("STATUS", "implemented"), ("MILESTONE", "@MILESTONE.M9")),
            create_task("S5", ("STATUS", "todo")),
        )

        # Act
        list_tasks_of_reached_milestones(self.processes, main)

        # Assert
        self.assertEqual(self.processes.list_argvs(), [])
