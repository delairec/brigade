import unittest

from tests.guards.read_task_milestones import read_task_milestones


class ReadTaskMilestonesTest(unittest.TestCase):
    def test_should_read_the_milestone_of_each_task(self):
        # Arrange
        tasks = (
            "TASK B7\n"
            '\tTITLE "brigade doctor inspects the prerequisites"\n'
            "\tSTATUS implemented\n"
            "\tMILESTONE @MILESTONE.M1\n"
            '\tSPEC "the milestone of the doctor"\n'
            '\t\tIMPL "brigade/commands/doctor.py::MILESTONE @MILESTONE.M9"\n'
            "\n"
            "TASK B257\n"
            '\tTITLE "the glossary"\n'
            "\tMILESTONE @MILESTONE.M8\n"
        )

        # Act
        milestones = read_task_milestones(tasks)

        # Assert
        self.assertEqual(milestones, {"B7": "M1", "B257": "M8"})
