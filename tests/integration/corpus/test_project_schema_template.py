import tempfile
import unittest
from pathlib import Path

from brigade.corpus.lint_corpus import lint_corpus
from brigade.corpus.read_entities import Entity, EntityField
from brigade.corpus.shipped_data import SHIPPED_PROJECT_SCHEMA
from brigade.registry.render_project_schema import render_project_schema
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
DELIVERED_WITH_NO_PULL_REQUEST = (
    'TASK T1\n\tTITLE "Delivered"\n\tSTATUS implemented\n\tTYPE fix\n'
    '\tSPEC "delivered"\n\t\tIMPL "src/cart.py::def add_item"\n'
)
DELIVERED_WITH_AN_ANCHOR_OUTSIDE_THE_AREA = (
    'TASK T1\n\tTITLE "Delivered"\n\tSTATUS implemented\n\tTYPE fix\n'
    '\tSPEC "delivered"\n\t\tIMPL "src/cart.py::def add_item"\n'
)
DELIVERED_WITH_NO_ANCHOR = 'TASK T1\n\tTITLE "Delivered"\n\tSTATUS implemented\n\tTYPE fix\n\tSPEC "delivered"\n'


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

    def test_should_pass_the_strict_lint_of_a_task_delivered_with_no_pull_request(self):
        # Arrange
        (self.root / "src").mkdir()
        (self.root / "src" / "cart.py").write_text("def add_item(): pass\n")
        (self.root / "corpus" / "plan.awawa").write_text(DELIVERED_WITH_NO_PULL_REQUEST)

        # Act
        report = lint_corpus(self.run_process, self.root)

        # Assert
        self.assertTrue(report.clean, report.output)

    def test_should_declare_the_status_ladders_the_tick_reads(self):
        # Act
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


class ProjectSchemaOfAnAreaTest(unittest.TestCase):
    def setUp(self):
        self.run_process = create_process_runner(provide_awawa(self))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.area = self.root / "brigade"
        self.area.mkdir()
        project = Entity(name="app", fields=(EntityField(name="MODE", value="area"),))
        (self.area / "_schema.awawa").write_text(render_project_schema(project))

    def test_should_pass_the_strict_lint_of_a_task_anchored_outside_the_area(self):
        # Arrange
        (self.area / "plan.awawa").write_text(DELIVERED_WITH_AN_ANCHOR_OUTSIDE_THE_AREA)

        # Act
        report = lint_corpus(self.run_process, self.area)

        # Assert
        self.assertTrue(report.clean, report.output)

    def test_should_still_require_an_impl_on_each_spec_of_an_implemented_task(self):
        # Arrange
        (self.area / "plan.awawa").write_text(DELIVERED_WITH_NO_ANCHOR)

        # Act
        report = lint_corpus(self.run_process, self.area)

        # Assert
        self.assertFalse(report.clean, report.output)
