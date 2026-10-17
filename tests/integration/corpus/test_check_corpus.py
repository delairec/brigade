import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from brigade.corpus.check_corpus import CorpusCheck, check_corpus
from brigade.system.run_process import ProcessRecord
from tests.awawa.provide_awawa import provide_awawa
from tests.integration.run_process_without_trail import run_process_without_trail

SCHEMA = 'SCHEMA TASK\n\tDESC "a change"\n\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n'
CANONICAL_TASKS = "TASK S2\n\tSTATUS implemented\n"
UNFORMATTED_TASKS = "TASK S2\n    STATUS implemented\n"
UNDECLARED_STATUS_TASKS = "TASK S2\n\tSTATUS shipped\n"


class CheckCorpusTest(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)

    def tearDown(self):
        self.root.cleanup()

    def test_should_check_the_format_then_the_lint_of_a_conformant_corpus(self):
        # Arrange
        (self.corpus / "tasks.awawa").write_text(CANONICAL_TASKS)

        # Act
        checks = check_corpus(run_process_without_trail, self.corpus)

        # Assert
        self.assertEqual(
            checks,
            (
                CorpusCheck(
                    command="awawa fmt --check .",
                    record=ProcessRecord(
                        argv=("awawa", "fmt", "--check", "."),
                        cwd=str(self.corpus),
                        exit_code=0,
                        stdout=ANY,
                        stderr=ANY,
                        duration_ms=ANY,
                    ),
                ),
                CorpusCheck(
                    command="awawa lint --strict .",
                    record=ProcessRecord(
                        argv=("awawa", "lint", "--strict", "."),
                        cwd=str(self.corpus),
                        exit_code=0,
                        stdout=ANY,
                        stderr=ANY,
                        duration_ms=ANY,
                    ),
                ),
            ),
        )

    def test_should_answer_the_failing_exit_code_of_a_corpus_awawa_fmt_would_rewrite(self):
        # Arrange
        (self.corpus / "tasks.awawa").write_text(UNFORMATTED_TASKS)

        # Act
        checks = check_corpus(run_process_without_trail, self.corpus)

        # Assert
        self.assertEqual(checks[0].record.exit_code, 1)

    def test_should_answer_the_failing_exit_code_of_a_corpus_lint_refuses(self):
        # Arrange
        (self.corpus / "tasks.awawa").write_text(UNDECLARED_STATUS_TASKS)

        # Act
        checks = check_corpus(run_process_without_trail, self.corpus)

        # Assert
        self.assertEqual(checks[1].record.exit_code, 1)
