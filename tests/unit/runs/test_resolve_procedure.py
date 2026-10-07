import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.resolve_procedure import ProcedureDirectories, resolve_procedure

SHIPPED_REVIEW = "---\ncapabilities: read\nbudget: 30\n---\nReview as brigade ships it.\n"
CORPUS_REVIEW = "---\ncapabilities: read, shell\nbudget: 40\n---\nReview as the instructions corpus says.\n"
CORPUS_TRIAGE = "---\ncapabilities: read\nbudget: 15\n---\nTriage the open issues.\n"


class ResolveProcedureByNameTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.shipped = Path(self.root.name) / "shipped"
        self.shipped.mkdir()
        self.instructions = Path(self.root.name) / "instructions"
        (self.instructions / "procedures").mkdir(parents=True)
        (self.shipped / "review.md").write_text(SHIPPED_REVIEW)
        (self.instructions / "procedures" / "review.md").write_text(CORPUS_REVIEW)
        (self.instructions / "procedures" / "triage.md").write_text(CORPUS_TRIAGE)
        self.directories = ProcedureDirectories(shipped=self.shipped, instructions=str(self.instructions))

    def tearDown(self):
        self.root.cleanup()


class ResolveProcedureShippedAndInTheCorpusTest(ResolveProcedureByNameTestCase):
    def test_should_resolve_the_procedure_brigade_ships(self):
        # Act
        procedure = resolve_procedure("review", self.directories)

        # Assert
        self.assertEqual(procedure.location, str(self.shipped / "review.md"))


class ResolveProcedureOnlyInTheCorpusTest(ResolveProcedureByNameTestCase):
    def test_should_fall_through_to_the_procedures_of_the_instructions_corpus(self):
        # Act
        procedure = resolve_procedure("triage", self.directories)

        # Assert
        self.assertEqual(procedure.location, str(self.instructions / "procedures" / "triage.md"))


class ResolveProcedureFoundNowhereTest(ResolveProcedureByNameTestCase):
    def test_should_refuse_naming_the_procedure_and_where_it_was_sought(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_procedure("deploy", self.directories)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"no procedure deploy: not shipped with brigade and not in {self.instructions}/procedures",
        )


class ResolveProcedureFoundNowhereWithoutAnInstructionsCorpusTest(unittest.TestCase):
    def test_should_refuse_naming_the_procedure_and_that_no_corpus_is_set(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        shipped = Path(root.name) / "shipped"
        shipped.mkdir()
        directories = ProcedureDirectories(shipped=shipped, instructions=None)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_procedure("deploy", directories)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "no procedure deploy: not shipped with brigade and no instructions corpus set in config.toml",
        )


class ResolveProcedureByPathTest(unittest.TestCase):
    def test_should_resolve_a_procedure_given_by_its_path(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "custom.md"
        path.write_text("---\ncapabilities: read\nbudget: 10\n---\nCustom procedure.\n")
        directories = ProcedureDirectories(shipped=Path(root.name), instructions=None)

        # Act
        procedure = resolve_procedure(str(path), directories)

        # Assert
        self.assertEqual(procedure.name, "custom")
        self.assertEqual(procedure.location, str(path))

    def test_should_refuse_a_path_that_is_not_a_file(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "missing.md"
        directories = ProcedureDirectories(shipped=Path(root.name), instructions=None)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_procedure(str(path), directories)

        # Assert
        self.assertEqual(str(raised.exception), f"no procedure file {path}")


class ResolveProcedureWithAnUnknownCapabilityTest(unittest.TestCase):
    def test_should_refuse_a_procedure_declaring_a_capability_outside_the_set(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "bad.md"
        path.write_text("---\ncapabilities: read, fly\nbudget: 10\n---\nBad procedure.\n")
        directories = ProcedureDirectories(shipped=Path(root.name), instructions=None)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_procedure(str(path), directories)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"the procedure {path} declares fly, not one of read, write, shell, net",
        )


class ResolveProcedureWithAnInvalidBudgetTest(unittest.TestCase):
    def test_should_refuse_a_procedure_whose_budget_is_not_a_positive_integer(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "bad.md"
        path.write_text("---\ncapabilities: read\nbudget: zero\n---\nBad procedure.\n")
        directories = ProcedureDirectories(shipped=Path(root.name), instructions=None)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_procedure(str(path), directories)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"the procedure {path} has the budget zero, not a positive integer",
        )
