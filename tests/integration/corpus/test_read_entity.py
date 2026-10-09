import os
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.corpus.read_entity import read_entity
from brigade.errors import EntityNotDefined, ToolFailure
from tests.integration.run_process_without_trail import run_process_without_trail

SCHEMA = 'SCHEMA AGENT\n\tDESC "a role"\n\tFIELD WORK string\n\t\tREPEATABLE\n\tFIELD BUDGET uint\n'
AGENTS = 'AGENT planner\n\tWORK "the plan of a wave"\n\tWORK "the order of its tasks"\n\tBUDGET 40\n'


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class ReadEntityTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)
        (self.corpus / "agents.awawa").write_text(AGENTS)

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_fields_of_one_entity_unquoted_in_their_order(self):
        # Act
        entity = read_entity(run_process_without_trail, self.corpus, "AGENT", "planner")

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

    def test_should_refuse_an_entity_the_corpus_does_not_define_naming_it(self):
        # Act
        with self.assertRaises(EntityNotDefined) as refusal:
            read_entity(run_process_without_trail, self.corpus, "AGENT", "nobody")

        # Assert
        self.assertEqual(str(refusal.exception), f"@AGENT.nobody is not defined in {self.corpus}")

    @unittest.skipIf(os.geteuid() == 0, "root reads what the permissions refuse")
    def test_should_refuse_an_unreadable_corpus_with_the_stderr_of_awawa(self):
        # Arrange
        agents = self.corpus / "agents.awawa"
        agents.chmod(0o000)

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            read_entity(run_process_without_trail, self.corpus, "AGENT", "planner")

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"awawa show @AGENT.planner --json {self.corpus} exited 2:"
            f" awawa: {agents}: Permission denied (os error 13)",
        )
