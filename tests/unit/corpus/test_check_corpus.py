import unittest
from pathlib import Path

from brigade.corpus.check_corpus import CorpusCheck, check_corpus
from brigade.system.run_process import ProcessRecord
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class CheckCorpusTest(unittest.TestCase):
    def test_should_run_the_format_and_lint_checks_and_keep_each_verdict(self):
        # Arrange
        awawa = RecordingProcessRunner({("awawa", "lint", "--strict", "."): ProcessAnswer(exit_code=1)})

        # Act
        checks = check_corpus(awawa, Path("/srv/shop"))

        # Assert
        self.assertEqual(
            checks,
            (
                CorpusCheck(
                    command="awawa fmt --check .",
                    record=ProcessRecord(
                        argv=("awawa", "fmt", "--check", "."),
                        cwd="/srv/shop",
                        exit_code=0,
                        stdout="",
                        stderr="",
                        duration_ms=0,
                    ),
                ),
                CorpusCheck(
                    command="awawa lint --strict .",
                    record=ProcessRecord(
                        argv=("awawa", "lint", "--strict", "."),
                        cwd="/srv/shop",
                        exit_code=1,
                        stdout="",
                        stderr="",
                        duration_ms=0,
                    ),
                ),
            ),
        )
