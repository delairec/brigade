import tempfile
import unittest
from pathlib import Path

from brigade.corpus.check_type_declared import check_type_declared
from tests.awawa.provide_awawa import provide_awawa
from tests.integration.run_process_without_trail import run_process_without_trail

SCHEMA = 'SCHEMA FINDING\n\tDESC "what a study found"\n\tFIELD TITLE string\n'


class CheckTypeDeclaredTest(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)

    def tearDown(self):
        self.root.cleanup()

    def test_should_tell_a_type_the_schema_declares_from_one_it_does_not(self):
        # Act
        declared = (
            check_type_declared(run_process_without_trail, self.corpus, "FINDING"),
            check_type_declared(run_process_without_trail, self.corpus, "VERDICT"),
        )

        # Assert
        self.assertEqual(declared, (True, False))
