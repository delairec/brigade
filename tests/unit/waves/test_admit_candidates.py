import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.waves.admit_candidates import admit_candidates
from brigade.waves.read_project_tasks import ProjectTasks
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

ROOT = Path("/srv/shop")
NO_INCOMING_REFERENCE = {"incoming": []}
NO_OPEN_TASK = {}
NO_IMPLEMENTED_TASK = frozenset()
NO_MILESTONE = None
TODO = EntityField(name="STATUS", value="todo")
TASK_OF_M2 = Entity(name="B1", fields=(TODO, EntityField(name="MILESTONE", value="@MILESTONE.M2")))
TASK_OF_M3 = Entity(name="B2", fields=(TODO, EntityField(name="MILESTONE", value="@MILESTONE.M3")))
TASK_OF_NO_MILESTONE = Entity(name="B3", fields=(TODO,))
TASK_AFTER_A_TASK_OF_M3 = Entity(name="B4", fields=(TODO, EntityField(name="AFTER", value="@TASK.B2")))
EVERY_TASK = {"B1": TASK_OF_M2, "B2": TASK_OF_M3, "B3": TASK_OF_NO_MILESTONE}


class AdmitCandidatesOfTheirMilestoneTest(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()
        for task in ("B1", "B2", "B3", "B4"):
            self.processes.answer_json(("awawa", "refs", f"@TASK.{task}", "--json", str(ROOT)), NO_INCOMING_REFERENCE)
        self.runtime = create_test_runtime(run_process=self.processes)

    def test_should_admit_only_the_tasks_naming_the_milestone_read(self):
        # Arrange
        tasks = ProjectTasks(root=ROOT, by_name=EVERY_TASK, implemented=NO_IMPLEMENTED_TASK, milestone="M2")

        # Act
        admitted = admit_candidates(self.runtime, tasks, NO_OPEN_TASK)

        # Assert
        self.assertEqual(admitted, ("B1",))

    def test_should_admit_only_the_tasks_naming_no_milestone_when_none_is_read(self):
        # Arrange
        tasks = ProjectTasks(root=ROOT, by_name=EVERY_TASK, implemented=NO_IMPLEMENTED_TASK, milestone=NO_MILESTONE)

        # Act
        admitted = admit_candidates(self.runtime, tasks, NO_OPEN_TASK)

        # Assert
        self.assertEqual(admitted, ("B3",))

    def test_should_leave_out_a_task_coming_after_a_task_of_another_milestone(self):
        # Arrange
        tasks = ProjectTasks(
            root=ROOT,
            by_name={"B2": TASK_OF_M3, "B4": TASK_AFTER_A_TASK_OF_M3},
            implemented=NO_IMPLEMENTED_TASK,
            milestone=NO_MILESTONE,
        )

        # Act
        admitted = admit_candidates(self.runtime, tasks, NO_OPEN_TASK)

        # Assert
        self.assertEqual(admitted, ())


if __name__ == "__main__":
    unittest.main()
