import tempfile
import unittest
from pathlib import Path

from brigade.corpus.lint_corpus import lint_corpus
from brigade.corpus.shipped_data import SHIPPED_PROJECT_SCHEMA
from tests.awawa.provide_awawa import provide_awawa
from tests.create_process_runner import create_process_runner

EVERY_STATUS_AND_FIELD = (
    'MILESTONE M1\n\tTITLE "Planned"\n\tSTATUS planned\n\n'
    'MILESTONE M2\n\tTITLE "Active"\n\tSTATUS active\n\n'
    'MILESTONE M3\n\tTITLE "Reached"\n\tSTATUS reached\n\n'
    'TASK T1\n\tTITLE "A draft"\n\tSTATUS draft\n\tSPEC "drafted"\n\n'
    'TASK T2\n\tTITLE "Ratified"\n\tSTATUS todo\n\tTYPE feat\n\tMILESTONE @MILESTONE.M2\n\tSPEC "ratified"\n\n'
    'TASK T3\n\tTITLE "Delivered"\n\tSTATUS implemented\n\tTYPE fix\n\tMILESTONE @MILESTONE.M3\n'
    '\tAFTER @TASK.T2\n\tDELIVERED_BY 12\n\tSPEC "delivered"\n\t\tIMPL "src/cart.py::def add_item"\n\n'
    'TASK T4\n\tTITLE "Retired"\n\tSTATUS archived\n\tSPEC "retired"\n\n'
    'DECISION CartLivesInMemory\n\tTITLE "the cart lives in memory"\n\tSTATUS active\n\n'
    'OPEN_QUESTION WhereTheCartLives\n\tQUESTION "where does the cart live?"\n\tSTATUS open\n\tBLOCKS @TASK.T1\n'
)


class ProjectSchemaTemplateTest(unittest.TestCase):
    def setUp(self):
        self.run_process = create_process_runner(provide_awawa(self))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "corpus").mkdir()
        (self.root / "corpus" / "_schema.awawa").write_text(SHIPPED_PROJECT_SCHEMA.read_text())

    def test_should_pass_the_strict_lint_with_no_entity_yet(self):
        # Act
        report = lint_corpus(self.run_process, self.root)

        # Assert
        self.assertTrue(report.clean, report.output)

    def test_should_pass_the_strict_lint_of_every_status_and_field_a_plan_and_a_tick_read(self):
        # Arrange
        (self.root / "src").mkdir()
        (self.root / "src" / "cart.py").write_text("def add_item(): pass\n")
        (self.root / "corpus" / "plan.awawa").write_text(EVERY_STATUS_AND_FIELD)

        # Act
        report = lint_corpus(self.run_process, self.root)

        # Assert
        self.assertTrue(report.clean, report.output)

    def test_should_declare_the_status_ladders_the_tick_reads(self):
        # Arrange
        schema = SHIPPED_PROJECT_SCHEMA.read_text()

        # Assert
        for declaration in [
            "FIELD STATUS draft|todo|implemented|archived\n",
            "FIELD STATUS planned|active|reached\n",
            "FIELD STATUS active|archived\n",
            "FIELD STATUS open|closed\n",
        ]:
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, schema)
