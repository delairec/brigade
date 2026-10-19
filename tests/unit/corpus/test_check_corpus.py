import unittest
from pathlib import Path

from brigade.corpus.check_corpus import check_corpus
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class CheckCorpusTest(unittest.TestCase):
    def test_should_run_the_format_and_lint_checks_and_keep_each_verdict(self):
        # Arrange
        awawa = RecordingProcessRunner({("awawa", "lint", "--strict", "."): ProcessAnswer(exit_code=1)})

        # Act
        checks = check_corpus(awawa, Path("/srv/shop"))

        # Assert
        self.assertEqual(
            [(check.command, check.record.exit_code) for check in checks],
            [("awawa fmt --check .", 0), ("awawa lint --strict .", 1)],
        )
