import unittest
from pathlib import Path

from brigade.git.list_commit_subjects import list_commit_subjects
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

LOG_SINCE_THE_BASE = ("git", "log", "--reverse", "--format=%s", "origin/main..8885daa", "--")


class ListCommitSubjectsTest(unittest.TestCase):
    def test_should_answer_the_subjects_of_the_head_since_its_base_oldest_first(self):
        # Arrange
        git = RecordingProcessRunner(
            {LOG_SINCE_THE_BASE: ProcessAnswer(stdout="feat(tick): open the wave\nfix(tick): keep the head\n")}
        )

        # Act
        subjects = list_commit_subjects(git, Path("/srv/shop"), "origin/main", "8885daa")

        # Assert
        self.assertEqual(subjects, ("feat(tick): open the wave", "fix(tick): keep the head"))

    def test_should_answer_none_for_a_head_at_its_base(self):
        # Arrange
        git = RecordingProcessRunner({LOG_SINCE_THE_BASE: ProcessAnswer(stdout="")})

        # Act
        subjects = list_commit_subjects(git, Path("/srv/shop"), "origin/main", "8885daa")

        # Assert
        self.assertEqual(subjects, ())
