import unittest
from pathlib import Path

from brigade.verify.check_corpus_at_head import check_corpus_at_head
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class CheckCorpusAtHeadTest(unittest.TestCase):
    def test_should_pass_a_corpus_formatted_and_linted(self):
        # Act
        check = check_corpus_at_head(RecordingProcessRunner(), Path("/cache/shop/2222222"))

        # Assert
        self.assertEqual(check, {"name": "corpus", "verdict": "pass", "findings": []})

    def test_should_fail_naming_the_check_and_its_output(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {("awawa", "lint", "--strict", "."): ProcessAnswer(exit_code=1, stdout="tasks.awawa:3: L002\n")}
        )

        # Act
        check = check_corpus_at_head(awawa, Path("/cache/shop/2222222"))

        # Assert
        self.assertEqual(
            check,
            {
                "name": "corpus",
                "verdict": "fail",
                "findings": ["awawa lint --strict . exited 1", "tasks.awawa:3: L002"],
            },
        )

    def test_should_fail_naming_the_check_of_the_format_and_its_output(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {
                ("awawa", "fmt", "--check", "."): ProcessAnswer(
                    exit_code=1, stdout="would reformat ./corpus/milestones.awawa\n"
                )
            }
        )

        # Act
        check = check_corpus_at_head(awawa, Path("/cache/shop/2222222"))

        # Assert
        self.assertEqual(
            check,
            {
                "name": "corpus",
                "verdict": "fail",
                "findings": ["awawa fmt --check . exited 1", "would reformat ./corpus/milestones.awawa"],
            },
        )
