import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity_template import read_entity_template
from tests.awawa.provide_awawa import provide_awawa
from tests.integration.run_process_without_trail import run_process_without_trail

SCHEMA = 'SCHEMA TASK\n\tDESC "a change"\n\tFIELD TITLE string\n\t\tREQUIRED\n\tFIELD SPEC string\n\t\tREPEATABLE\n'


class ReadEntityTemplateTest(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_template_of_a_declared_type_and_none_for_another(self):
        # Act
        templates = (
            read_entity_template(run_process_without_trail, self.corpus, "TASK", "B13"),
            read_entity_template(run_process_without_trail, self.corpus, "EPIC", "E1"),
        )

        # Assert
        self.assertEqual(templates, ("TASK B13\n\tTITLE // string\n\t// SPEC string\n", None))
