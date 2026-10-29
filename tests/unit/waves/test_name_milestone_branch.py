import unittest

from brigade.waves.name_milestone_branch import name_milestone_branch


class NameMilestoneBranchTest(unittest.TestCase):
    def test_should_name_the_branch_after_the_slug_of_the_title(self):
        rows = (
            ("Dashboard", "integration/dashboard"),
            ("Milestone integration branch", "integration/milestone-integration-branch"),
            ("  Empty cart — v2!  ", "integration/empty-cart-v2"),
            ("Café", "integration/caf"),
        )
        for title, expected in rows:
            with self.subTest(title=title):
                # Act
                branch = name_milestone_branch(title)

                # Assert
                self.assertEqual(branch, expected)
