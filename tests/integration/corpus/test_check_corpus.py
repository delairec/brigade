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
REPORT_OF_A_WAVE = (
    "REPORT shop_w2\n"
    '\tWAVE "shop_w2"\n'
    '\tPROJECT "shop"\n'
    '\tTASK_ROW "B17 merged #178"\n'
    '\tSTATISTIC "tasks merged 1"\n'
    '\tGRAPH "B20 after B17"\n'
    '\tMANUAL_TEST "B17: the task becomes merged"\n'
    '\tINSTRUCTIONS_CHANGE "corpus/tasks.awawa +12 -3"\n'
    '\tPARKED_QUESTION "B21 blocked by @OPEN_QUESTION.TheKeyOfAWave"\n'
    '\tNARRATIVE "one task merged"\n'
    '\tREASON "B21 waits for a ruling"\n'
    '\tTESTER_STEP "open the dashboard and see B17 merged"\n'
    '\tSAMPLING "read the merge of B17"\n'
)


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
        self.assertEqual(
            checks,
            (
                CorpusCheck(
                    command="awawa fmt --check .",
                    record=ProcessRecord(
                        argv=("awawa", "fmt", "--check", "."),
                        cwd=str(self.corpus),
                        exit_code=1,
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
                        exit_code=1,
                        stdout=ANY,
                        stderr=ANY,
                        duration_ms=ANY,
                    ),
                ),
            ),
        )

    def test_should_answer_the_failing_exit_code_of_a_corpus_lint_refuses(self):
        # Arrange
        (self.corpus / "tasks.awawa").write_text(UNDECLARED_STATUS_TASKS)

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
                        exit_code=1,
                        stdout=ANY,
                        stderr=ANY,
                        duration_ms=ANY,
                    ),
                ),
            ),
        )

    def test_should_lint_clean_a_policy_asking_for_the_wave_starts_of_its_project_under_the_shipped_schema(self):
        # Arrange
        shutil.copyfile(SHIPPED_SCHEMA, self.corpus / "_schema.awawa")
        (self.corpus / "projects.awawa").write_text(SHOP_PROJECT)
        (self.corpus / "policies.awawa").write_text(POLICY_ASKING_FOR_WAVE_STARTS)

        # Act
        checks = check_corpus(self.run_process, self.corpus)

        # Assert
        self.assertEqual(checks[1].record.exit_code, 0, checks[1].record.stdout)


class CheckCorpusUnderTheShippedSchemaTest(unittest.TestCase):
    def setUp(self):
        self.run_process = create_process_runner(provide_awawa(self))
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.corpus = Path(self.root.name)
        shutil.copyfile(SHIPPED_SCHEMA, self.corpus / "_schema.awawa")

    def test_should_find_a_corpus_holding_the_shipped_schema_alone_clean(self):
        # Act
        checks = check_corpus(self.run_process, self.corpus)

        # Assert
        self.assertEqual(checks[0].record.exit_code, 0, checks[0].record.stdout)
        self.assertEqual(checks[1].record.exit_code, 0, checks[1].record.stdout)

    def test_should_accept_a_review_by_approval_or_verdict_only(self):
        # Arrange
        (self.corpus / "projects.awawa").write_text(SHOP_PROJECT)
        rows = [
            ("approval", "POLICY shop_policy\n\tPROJECT @PROJECT.shop\n\tREVIEW approval\n", 0),
            ("verdict", "POLICY shop_policy\n\tPROJECT @PROJECT.shop\n\tREVIEW verdict\n", 0),
            ("local", "POLICY shop_policy\n\tPROJECT @PROJECT.shop\n\tREVIEW local\n", 1),
        ]
        for review, policy, expected_exit_code in rows:
            with self.subTest(review=review):
                # Arrange
                (self.corpus / "policies.awawa").write_text(policy)

                # Act
                checks = check_corpus(self.run_process, self.corpus)

                # Assert
                self.assertEqual(checks[1].record.exit_code, expected_exit_code, checks[1].record.stdout)

    def test_should_accept_the_report_of_a_wave(self):
        # Arrange
        (self.corpus / "reports.awawa").write_text(REPORT_OF_A_WAVE)

        # Act
        checks = check_corpus(self.run_process, self.corpus)

        # Assert
        self.assertEqual(checks[1].record.exit_code, 0, checks[1].record.stdout)
