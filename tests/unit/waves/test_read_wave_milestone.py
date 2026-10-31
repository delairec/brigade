import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.waves.read_wave_milestone import read_wave_milestone

TODO = EntityField(name="STATUS", value="todo")
TASK_OF_M3 = Entity(name="B1", fields=(TODO, EntityField(name="MILESTONE", value="@MILESTONE.M3")))
OTHER_TASK_OF_M3 = Entity(name="B2", fields=(TODO, EntityField(name="MILESTONE", value="@MILESTONE.M3")))
TASK_OF_M4 = Entity(name="B3", fields=(TODO, EntityField(name="MILESTONE", value="@MILESTONE.M4")))
TASK_OF_NO_MILESTONE = Entity(name="B4", fields=(TODO,))


class ReadWaveMilestoneTest(unittest.TestCase):
    def test_should_read_the_milestone_every_task_of_the_wave_names(self):
        # Act
        milestone = read_wave_milestone("shop_w2", (TASK_OF_M3, OTHER_TASK_OF_M3))

        # Assert
        self.assertEqual(milestone, "M3")

    def test_should_read_no_milestone_for_tasks_naming_none(self):
        # Act
        milestone = read_wave_milestone("shop_w2", (TASK_OF_NO_MILESTONE,))

        # Assert
        self.assertIsNone(milestone)

    def test_should_refuse_a_wave_whose_tasks_name_two_milestones(self):
        # Arrange
        rows = ((TASK_OF_M3, TASK_OF_M4), (TASK_OF_M3, TASK_OF_NO_MILESTONE))
        for tasks in rows:
            with self.subTest(tasks=tasks):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    read_wave_milestone("shop_w2", tasks)

                # Assert
                self.assertIn("the tasks of the wave shop_w2 name more than one milestone", str(refusal.exception))
