import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from tests.awawa.provide_awawa import provide_awawa
from tests.create_process_runner import create_process_runner

SCHEMA = 'SCHEMA TASK\n\tDESC "a change"\n\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n'
TASKS = "TASK S2\n\tSTATUS implemented\n\nTASK S3\n\tSTATUS todo\n"


class ReadAwawaDocumentTest(unittest.TestCase):
    def setUp(self):
        self.run_process = create_process_runner(provide_awawa(self))
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)
        (self.corpus / "tasks.awawa").write_text(TASKS)

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_json_document_of_the_awawa_command_on_the_corpus(self):
        # Act
        document = read_awawa_document(
            self.run_process, self.corpus, ("status", "TASK", "--where", "STATUS==implemented")
        )

        # Assert
        self.assertEqual(
            document["entities"],
            [
                {
                    "type": "TASK",
                    "name": "S2",
                    "target": "@TASK.S2",
                    "file": str(self.corpus / "tasks.awawa"),
                    "line": 1,
                    "status": "implemented",
                    "incoming": 0,
                    "incoming_by": [],
                }
            ],
        )
