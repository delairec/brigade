import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.waves.admit_candidates import admit_candidates
from brigade.waves.read_project_tasks import ProjectTasks
from tests.unit.scripted_processes import ScriptedProcesses

ROOT = Path("/srv/shop")
ACTIVE_MILESTONES = ("awawa", "status", "MILESTONE", "--where", "STATUS==active", "--json", str(ROOT))
NO_INCOMING_REFERENCE = {"incoming": []}
NO_OPEN_TASK = {}
NO_IMPLEMENTED_TASK = frozenset()
TODO = EntityField(name="STATUS", value="todo")
TASK_OF_AN_ACTIVE_MILESTONE = Entity(name="B1", fields=(TODO, EntityField(name="MILESTONE", value="@MILESTONE.M2")))
TASK_OF_A_PLANNED_MILESTONE = Entity(name="B2", fields=(TODO, EntityField(name="MILESTONE", value="@MILESTONE.M3")))
TASK_OF_NO_MILESTONE = Entity(name="B3", fields=(TODO,))
TASK_AFTER_A_TASK_OF_A_PLANNED_MILESTONE = Entity(name="B4", fields=(TODO, EntityField(name="AFTER", value="@TASK.B2")))


class AdmitCandidatesOfTheirMilestoneTest(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()
        self.processes.answer_json(ACTIVE_MILESTONES, {"entities": [{"type": "MILESTONE", "name": "M2"}]})
        self.processes.answer_json(("awawa", "refs", "@TASK.B1", "--json", str(ROOT)), NO_INCOMING_REFERENCE)
        self.processes.answer_json(("awawa", "refs", "@TASK.B2", "--json", str(ROOT)), NO_INCOMING_REFERENCE)
        self.processes.answer_json(("awawa", "refs", "@TASK.B3", "--json", str(ROOT)), NO_INCOMING_REFERENCE)
        self.processes.answer_json(("awawa", "refs", "@TASK.B4", "--json", str(ROOT)), NO_INCOMING_REFERENCE)

    def test_should_admit_only_the_tasks_of_an_active_milestone_or_of_none(self):
        # Arrange
        tasks = ProjectTasks(
            root=ROOT,
            by_name={"B1": TASK_OF_AN_ACTIVE_MILESTONE, "B2": TASK_OF_A_PLANNED_MILESTONE, "B3": TASK_OF_NO_MILESTONE},
            implemented=NO_IMPLEMENTED_TASK,
        )

        # Act
        admitted = admit_candidates(self.processes, tasks, NO_OPEN_TASK)

        # Assert
        self.assertEqual(admitted, ("B1", "B3"))

    def test_should_leave_out_a_task_coming_after_a_task_of_a_milestone_not_active(self):
        # Arrange
        tasks = ProjectTasks(
            root=ROOT,
            by_name={"B2": TASK_OF_A_PLANNED_MILESTONE, "B4": TASK_AFTER_A_TASK_OF_A_PLANNED_MILESTONE},
            implemented=NO_IMPLEMENTED_TASK,
        )

        # Act
        admitted = admit_candidates(self.processes, tasks, NO_OPEN_TASK)

        # Assert
        self.assertEqual(admitted, ())

    def test_should_read_no_milestone_when_no_candidate_names_one(self):
        # Arrange
        tasks = ProjectTasks(root=ROOT, by_name={"B3": TASK_OF_NO_MILESTONE}, implemented=NO_IMPLEMENTED_TASK)

        # Act
        admit_candidates(self.processes, tasks, NO_OPEN_TASK)

        # Assert
        self.assertNotIn(ACTIVE_MILESTONES, self.processes.list_argvs())


if __name__ == "__main__":
    unittest.main()
