import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.waves.read_project_tasks import ProjectTasks
from brigade.waves.read_served_milestones import ServedMilestones, WaitingMilestone, read_served_milestones
from tests.unit.scripted_processes import ScriptedProcesses

ROOT = Path("/cache/refs/shop/4f1c2a9")
ACTIVE_MILESTONES = ("awawa", "status", "MILESTONE", "--where", "STATUS==active", "--json", str(ROOT))
REACHED_MILESTONES = ("awawa", "status", "MILESTONE", "--where", "STATUS==reached", "--json", str(ROOT))
NO_TASK_IMPLEMENTED = frozenset()
READ_AT_MAIN = None
S1_TODO_OF_M9 = Entity(
    name="S1", fields=(EntityField(name="STATUS", value="todo"), EntityField(name="MILESTONE", value="@MILESTONE.M9"))
)
S2_TODO_NAMING_NO_MILESTONE = Entity(name="S2", fields=(EntityField(name="STATUS", value="todo"),))


def create_main(by_name: dict[str, Entity]) -> ProjectTasks:
    return ProjectTasks(root=ROOT, by_name=by_name, implemented=NO_TASK_IMPLEMENTED, milestone=READ_AT_MAIN)


class ReadServedMilestonesTest(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()
        self.processes.answer_entities(
            ROOT,
            "MILESTONE",
            {
                "M9": (("STATUS", "active"),),
                "M10": (("STATUS", "active"), ("AFTER", "@MILESTONE.M5")),
                "M11": (("STATUS", "active"), ("AFTER", "@MILESTONE.M5"), ("AFTER", "@MILESTONE.M9")),
            },
            ("STATUS==active",),
        )
        self.processes.answer_entities(ROOT, "MILESTONE", {"M5": (("STATUS", "reached"),)}, ("STATUS==reached",))

    def test_should_serve_the_active_milestones_whose_after_is_reached_or_absent_in_the_order_of_the_corpus(self):
        # Act
        milestones = read_served_milestones(self.processes, create_main({"S1": S1_TODO_OF_M9}))

        # Assert
        self.assertEqual(milestones.served, ("M9", "M10"))

    def test_should_keep_waiting_an_active_milestone_with_the_after_not_reached(self):
        # Act
        milestones = read_served_milestones(self.processes, create_main({"S1": S1_TODO_OF_M9}))

        # Assert
        self.assertEqual(milestones.waiting, (WaitingMilestone(milestone="M11", after=("@MILESTONE.M9",)),))

    def test_should_read_no_reached_milestone_when_no_active_milestone_names_an_after(self):
        # Arrange
        processes = ScriptedProcesses()
        processes.answer_entities(ROOT, "MILESTONE", {"M9": (("STATUS", "active"),)}, ("STATUS==active",))

        # Act
        milestones = read_served_milestones(processes, create_main({"S1": S1_TODO_OF_M9}))

        # Assert
        self.assertEqual(milestones, ServedMilestones(served=("M9",), waiting=()))

    def test_should_read_no_milestone_when_no_task_names_one(self):
        # Act
        milestones = read_served_milestones(self.processes, create_main({"S2": S2_TODO_NAMING_NO_MILESTONE}))

        # Assert
        self.assertEqual(milestones, ServedMilestones(served=(), waiting=()))


if __name__ == "__main__":
    unittest.main()
