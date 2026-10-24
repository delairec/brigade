import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_schema import read_schema
from tests.awawa.provide_awawa import provide_awawa
from tests.create_process_runner import create_process_runner

SHIPPED_SCHEMA = Path(__file__).resolve().parents[3] / "brigade" / "corpus" / "data" / "schema.awawa.tpl"
SCHEMA = 'SCHEMA TASK\n\tDESC "a change"\n\tFIELD TITLE string\n\t\tREQUIRED\n\tFIELD SPEC string\n\t\tREPEATABLE\n'


class ReadSchemaTest(unittest.TestCase):
    def setUp(self):
        self.run_process = create_process_runner(provide_awawa(self))
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_schema_of_a_declared_type_and_none_for_another(self):
        # Act
        schemas = (
            read_schema(self.run_process, self.corpus, "TASK"),
            read_schema(self.run_process, self.corpus, "MILESTONE"),
        )

        # Assert
        self.assertEqual(
            schemas,
            (
                (
                    'SCHEMA TASK\n\tDESC "a change"\n\tFIELD TITLE string\n\t\tREQUIRED\n\tFIELD SPEC string\n'
                    "\t\tREPEATABLE\n"
                ),
                None,
            ),
        )


class ReadSchemaOfTheShippedSchemaTest(unittest.TestCase):
    def setUp(self):
        self.run_process = create_process_runner(provide_awawa(self))
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.corpus = Path(self.root.name)
        shutil.copyfile(SHIPPED_SCHEMA, self.corpus / "_schema.awawa")

    def test_should_merge_a_project_by_rebase_by_default(self):
        # Act
        schema = read_schema(self.run_process, self.corpus, "PROJECT")

        # Assert
        self.assertIn("\tFIELD MERGE squash|rebase|merge\n\t\tDEFAULT rebase\n", schema)
