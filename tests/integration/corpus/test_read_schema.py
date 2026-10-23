import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_schema import read_schema
from tests.awawa.provide_awawa import provide_awawa
from tests.create_process_runner import create_process_runner

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
