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


class ResolveProcedureWithNoInstructionsCorpusTest(ResolveProcedureByNameTestCase):
    def test_should_refuse_naming_the_missing_instructions_corpus(self):
        # Arrange
        directories = ProcedureDirectories(shipped=self.shipped, instructions=None)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_procedure("triage", directories)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "no procedure triage: not shipped with brigade and no instructions corpus set in config.toml",
        )


class ResolveProcedureGivenByPathTest(ResolveProcedureByNameTestCase):
    def test_should_refuse_a_path_to_no_file(self):
        # Arrange
        missing = Path(self.root.name) / "procedures" / "deliver.md"

        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_procedure(str(missing), self.directories)

        # Assert
        self.assertEqual(str(raised.exception), f"no procedure file {missing}")

    def test_should_refuse_a_front_matter_off_its_declaration(self):
        procedure = Path(self.root.name) / "deliver.md"
        rows = [
            (
                "---\ncapabilities: read, fly\nbudget: 10\n---\nBody.\n",
                f"the procedure {procedure} declares fly, not one of read, write, shell, net",
            ),
            (
                "---\ncapabilities: read\nbudget: many\n---\nBody.\n",
                f"the procedure {procedure} has the budget many, not a positive integer",
            ),
        ]
        for content, expected_refusal in rows:
            with self.subTest(content=content):
                # Arrange
                procedure.write_text(content)

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    resolve_procedure(str(procedure), self.directories)

                # Assert
                self.assertEqual(str(raised.exception), expected_refusal)
