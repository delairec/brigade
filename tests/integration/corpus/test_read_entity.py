import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.corpus.read_entity import read_entity
from brigade.system.run_process import run_process

SCHEMA = 'SCHEMA AGENT\n\tDESC "a role"\n\tFIELD WORK string\n\t\tREPEATABLE\n\tFIELD BUDGET uint\n'
AGENTS = 'AGENT planner\n\tWORK "the plan of a wave"\n\tWORK "the order of its tasks"\n\tBUDGET 40\n'


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class ReadEntity(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)
        (self.corpus / "agents.awawa").write_text(AGENTS)

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_fields_of_one_entity_unquoted_in_their_order(self):
        # Act
        entity = read_entity(run_process, self.corpus, "AGENT", "planner")

        # Assert
        self.assertEqual(
            entity,
            Entity(
                name="planner",
                fields=(
                    EntityField(name="WORK", value="the plan of a wave"),
                    EntityField(name="WORK", value="the order of its tasks"),
                    EntityField(name="BUDGET", value="40"),
                ),
            ),
        )
