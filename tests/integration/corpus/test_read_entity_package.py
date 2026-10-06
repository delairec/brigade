import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity_package import read_entity_package
from brigade.system.run_process import run_process

SCHEMA = (
    'SCHEMA AGENT\n\tDESC "a role"\n\tFIELD WORK string\n\tFIELD LOADS @RULE\n'
    "\tFIELD RATIONALE string\n\t\tCATEGORY reasoning\n\n"
    'SCHEMA RULE\n\tDESC "a rule"\n\tFIELD SPEC string\n'
)
AGENTS = (
    'AGENT planner\n\tWORK "the plan of a wave"\n\tLOADS @RULE.plans_are_short\n\tRATIONALE "why it plans"\n\n'
    'RULE plans_are_short\n\tSPEC "a plan fits one screen"\n'
)


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class ReadEntityPackage(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        (self.corpus / "_schema.awawa").write_text(SCHEMA)
        (self.corpus / "agents.awawa").write_text(AGENTS)

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_the_package_of_the_entity_and_what_it_rests_on_without_its_reasoning(self):
        # Act
        package = read_entity_package(run_process, self.corpus, "@AGENT.planner")

        # Assert
        self.assertEqual(
            package,
            "AGENT planner\n"
            '\tWORK "the plan of a wave"\n'
            "\tLOADS @RULE.plans_are_short\n"
            "\n"
            "RULE plans_are_short\n"
            '\tSPEC "a plan fits one screen"\n'
            "\n"
            "// context: 2 entities, 5 lines, depth 2\n"
            "// skipped (reasoning): 1 field on @AGENT.planner\n",
        )
