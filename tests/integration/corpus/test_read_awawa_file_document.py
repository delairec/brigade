import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_awawa_file_document import read_awawa_file_document
from tests.awawa.provide_awawa import provide_awawa
from tests.integration.run_process_without_trail import run_process_without_trail

SCHEMA = 'SCHEMA TASK\n\tDESC "a change"\n\tFIELD TITLE string\n\t\tREQUIRED\n'
PLAN = 'TASK B12\n\tTITLE "the parser"\n'


class ReadAwawaFileDocumentTest(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)
        self.plan_file = self.corpus / "plan.awawa"
        self.plan_file.write_text(PLAN)

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_json_document_of_the_awawa_command_on_one_file(self):
        # Act
        document = read_awawa_file_document(run_process_without_trail, self.plan_file, ("show", "@TASK.B12"))

        # Assert
        self.assertEqual(document["fields"], [{"name": "TITLE", "atoms": ['"the parser"'], "fields": []}])
