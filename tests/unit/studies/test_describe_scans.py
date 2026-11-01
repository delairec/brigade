import unittest

from brigade.studies.convert_study import Study
from brigade.studies.describe_scans import describe_scans


class DescribeScansTest(unittest.TestCase):
    def test_should_describe_the_four_daily_scans_of_the_project_answering_into_the_inbox(self):
        # Act
        scans = describe_scans("oak")

        # Assert
        self.assertEqual(
            scans,
            (
                Study(
                    name="corpus_lint_oak",
                    project="oak",
                    question=None,
                    collectors=("corpus-lint",),
                    slot="none",
                    every="24h",
                    output="inbox",
                    answer_type="ANSWER",
                    status="active",
                ),
                Study(
                    name="corpus_fmt_oak",
                    project="oak",
                    question=None,
                    collectors=("corpus-fmt",),
                    slot="none",
                    every="24h",
                    output="inbox",
                    answer_type="ANSWER",
                    status="active",
                ),
                Study(
                    name="stale_branches_oak",
                    project="oak",
                    question=None,
                    collectors=("stale-branches",),
                    slot="none",
                    every="24h",
                    output="inbox",
                    answer_type="ANSWER",
                    status="active",
                ),
                Study(
                    name="worktrees_oak",
                    project="oak",
                    question=None,
                    collectors=("stale-worktrees",),
                    slot="none",
                    every="24h",
                    output="inbox",
                    answer_type="ANSWER",
                    status="active",
                ),
            ),
        )
