import unittest

from brigade.tick.name_task_branch import name_task_branch

SHORT_TITLE = "Local mode"


class NameTaskBranchTest(unittest.TestCase):
    def test_should_prefix_the_branch_with_the_type_of_the_task_feat_becoming_feature(self):
        for task_type, expected in [
            ("build", "build/B46-local-mode"),
            ("chore", "chore/B46-local-mode"),
            ("ci", "ci/B46-local-mode"),
            ("docs", "docs/B46-local-mode"),
            ("feat", "feature/B46-local-mode"),
            ("fix", "fix/B46-local-mode"),
            ("perf", "perf/B46-local-mode"),
            ("refactor", "refactor/B46-local-mode"),
            ("revert", "revert/B46-local-mode"),
            ("style", "style/B46-local-mode"),
            ("test", "test/B46-local-mode"),
        ]:
            with self.subTest(task_type=task_type):
                # Act
                branch = name_task_branch(task_type, "B46", SHORT_TITLE)

                # Assert
                self.assertEqual(branch, expected)

    def test_should_slug_the_title_lowercased_with_one_hyphen_per_run_of_other_characters(self):
        for title, expected in [
            ("Local mode", "fix/B231-local-mode"),
            ("  Read the «ledger» -- twice!  ", "fix/B231-read-the-ledger-twice"),
            ("Crée l'été 2026", "fix/B231-cr-e-l-t-2026"),
        ]:
            with self.subTest(title=title):
                # Act
                branch = name_task_branch("fix", "B231", title)

                # Assert
                self.assertEqual(branch, expected)

    def test_should_cut_a_long_slug_at_its_last_hyphen_within_forty_characters(self):
        for title, expected in [
            (
                "A task runs on its own branch cut from its milestone",
                "feature/B232-a-task-runs-on-its-own-branch-cut-from",
            ),
            ("abcdefghij abcdefghij abcdefghij abcdefg xyz", "feature/B232-abcdefghij-abcdefghij-abcdefghij"),
            ("abcdefghij abcdefghij abcdefghij abcdef xyz", "feature/B232-abcdefghij-abcdefghij-abcdefghij-abcdef"),
            ("abcdefghij abcdefghij abcdefghij abcdefg", "feature/B232-abcdefghij-abcdefghij-abcdefghij-abcdefg"),
        ]:
            with self.subTest(title=title):
                # Act
                branch = name_task_branch("feat", "B232", title)

                # Assert
                self.assertEqual(branch, expected)

    def test_should_cut_a_long_slug_holding_no_hyphen_within_forty_characters_at_its_fortieth(self):
        # Arrange
        title = "abcdefghijabcdefghijabcdefghijabcdefghijabcdef tail"

        # Act
        branch = name_task_branch("feat", "B232", title)

        # Assert
        self.assertEqual(branch, "feature/B232-abcdefghijabcdefghijabcdefghijabcdefghij")
