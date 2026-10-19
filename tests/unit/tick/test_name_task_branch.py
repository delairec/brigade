import unittest

from brigade.tick.name_task_branch import name_task_branch


class NameTaskBranchTest(unittest.TestCase):
    def test_should_name_the_task_branch_after_the_wave_branch(self):
        for wave_branch, expected in [("integration/w1", "task/w1/B1"), ("main", "task/main/B1")]:
            with self.subTest(wave_branch=wave_branch):
                # Act
                branch = name_task_branch(wave_branch, "B1")

                # Assert
                self.assertEqual(branch, expected)
