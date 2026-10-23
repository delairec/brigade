import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from brigade.corpus.check_corpus import CorpusCheck, check_corpus
from brigade.system.run_process import ProcessRecord
from tests.awawa.provide_awawa import provide_awawa
from tests.create_process_runner import create_process_runner

SCHEMA = 'SCHEMA TASK\n\tDESC "a change"\n\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n'
CANONICAL_TASKS = "TASK S2\n\tSTATUS implemented\n"
UNFORMATTED_TASKS = "TASK S2\n    STATUS implemented\n"
UNDECLARED_STATUS_TASKS = "TASK S2\n\tSTATUS shipped\n"
SHIPPED_SCHEMA = Path(__file__).resolve().parents[3] / "brigade" / "corpus" / "data" / "schema.awawa.tpl"
SHOP_PROJECT = 'PROJECT shop\n\tPATH "/srv/shop"\n\tMAIN "main"\n\tSTATUS active\n'
POLICY_ASKING_FOR_WAVE_STARTS = "POLICY shop_waves\n\tPROJECT @PROJECT.shop\n\tWAVE_START ask\n"


class CheckCorpusTest(unittest.TestCase):
    def setUp(self):
        self.run_process = create_process_runner(provide_awawa(self))
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)

    def tearDown(self):
        self.root.cleanup()

    def test_should_check_the_format_then_the_lint_of_a_conformant_corpus(self):
        # Arrange
        (self.corpus / "tasks.awawa").write_text(CANONICAL_TASKS)

        # Act
        checks = check_corpus(self.run_process, self.corpus)

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
        checks = check_corpus(self.run_process, self.corpus)

        # Assert
        self.assertEqual(checks[0].record.exit_code, 1)

    def test_should_answer_the_failing_exit_code_of_a_corpus_lint_refuses(self):
        # Arrange
        (self.corpus / "tasks.awawa").write_text(UNDECLARED_STATUS_TASKS)

        # Act
        checks = check_corpus(self.run_process, self.corpus)

        # Assert
        self.assertEqual(checks[1].record.exit_code, 1)

    def test_should_lint_clean_a_policy_asking_for_the_wave_starts_of_its_project_under_the_shipped_schema(self):
        # Arrange
        shutil.copyfile(SHIPPED_SCHEMA, self.corpus / "_schema.awawa")
        (self.corpus / "projects.awawa").write_text(SHOP_PROJECT)
        (self.corpus / "policies.awawa").write_text(POLICY_ASKING_FOR_WAVE_STARTS)

        # Act
        checks = check_corpus(self.run_process, self.corpus)

        # Assert
        self.assertEqual(checks[1].record.exit_code, 0, checks[1].record.stdout)
