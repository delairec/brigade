import unittest
from pathlib import Path

from brigade.corpus.lint_corpus import LintReport, lint_corpus
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

LINT = ("awawa", "lint", "--strict", "/srv/shop")


class LintCorpusTest(unittest.TestCase):
    def test_should_report_a_clean_corpus(self):
        # Arrange
        awawa = RecordingProcessRunner()

        # Act
        report = lint_corpus(awawa, Path("/srv/shop"))

        # Assert
        self.assertEqual(report, LintReport(clean=True, output=""))

    def test_should_report_the_findings_of_both_streams(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {LINT: ProcessAnswer(exit_code=1, stdout="tasks.awawa:3: L002\n", stderr="1 error\n")}
        )

        # Act
        report = lint_corpus(awawa, Path("/srv/shop"))

        # Assert
        self.assertEqual(report, LintReport(clean=False, output="tasks.awawa:3: L002\n1 error"))
