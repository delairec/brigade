import unittest
from pathlib import Path

from brigade.git.read_upstream_lag import UpstreamLag, read_upstream_lag
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

BRANCHES = ("git", "for-each-ref", "--format=%(HEAD)%09%(objectname:short)%09%(upstream:short)", "refs/heads")
UPSTREAM_COMMIT = ("git", "rev-parse", "--short", "--verify", "--end-of-options", "origin/main")
COUNTS = ("git", "rev-list", "--left-right", "--count", "origin/main...HEAD")
ON_MAIN = " \t1111111\torigin/feat\n*\t2222222\torigin/main\n"


class ReadUpstreamLagBehindTest(unittest.TestCase):
    def test_should_answer_how_far_the_current_branch_is_behind_its_upstream(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                BRANCHES: ProcessAnswer(stdout=ON_MAIN),
                UPSTREAM_COMMIT: ProcessAnswer(stdout="3333333\n"),
                COUNTS: ProcessAnswer(stdout="3\t0\n"),
            }
        )

        # Act
        lag = read_upstream_lag(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(
            lag, UpstreamLag(commit="2222222", upstream="origin/main", upstream_commit="3333333", behind=3)
        )


class ReadUpstreamLagUpToDateTest(unittest.TestCase):
    def test_should_answer_none_for_a_branch_level_with_its_upstream(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                BRANCHES: ProcessAnswer(stdout=ON_MAIN),
                UPSTREAM_COMMIT: ProcessAnswer(stdout="2222222\n"),
                COUNTS: ProcessAnswer(stdout="0\t2\n"),
            }
        )

        # Act
        lag = read_upstream_lag(git, Path("/srv/shop"))

        # Assert
        self.assertIsNone(lag)


class ReadUpstreamLagWithoutUpstreamTest(unittest.TestCase):
    def test_should_answer_none_without_a_current_branch_tracking_an_upstream(self):
        for listing in [" \t1111111\torigin/feat\n", "*\t2222222\t\n"]:
            with self.subTest(listing=listing):
                # Arrange
                git = RecordingProcessRunner({BRANCHES: ProcessAnswer(stdout=listing)})

                # Act
                lag = read_upstream_lag(git, Path("/srv/shop"))

                # Assert
                self.assertIsNone(lag)
