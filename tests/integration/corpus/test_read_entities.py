import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField, read_entities
from brigade.system.run_process import run_process

SHIPPED_SCHEMA = Path(__file__).resolve().parents[3] / "brigade" / "corpus" / "data" / "schema.awawa.tpl"
PROJECTS = (
    "PROJECT zeta\n"
    '\tPATH "/srv/a \\"quoted\\" \\\\ path"\n'
    '\tMAIN "main"\n'
    '\tACCEPTANCE "make check"\n'
    '\tACCEPTANCE "make lint"\n'
    "\tSTATUS paused\n"
    "\n"
    "PROJECT alpha\n"
    '\tPATH "/srv/alpha"\n'
    '\tMAIN "trunk"\n'
    "\tSTATUS active\n"
)
POLICY = "POLICY alpha_policy\n\tPROJECT @PROJECT.alpha\n"


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class ReadEntities(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.corpus = Path(self.root.name)
        shutil.copyfile(SHIPPED_SCHEMA, self.corpus / "_schema.awawa")

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_every_entity_of_the_type_by_name_with_its_fields_unquoted(self):
        # Arrange
        (self.corpus / "projects.awawa").write_text(PROJECTS)
        (self.corpus / "policies.awawa").write_text(POLICY)

        # Act
        entities = read_entities(run_process, self.corpus, "PROJECT")

        # Assert
        self.assertEqual(
            entities,
            (
                Entity(
                    name="alpha",
                    fields=(
                        EntityField(name="PATH", value="/srv/alpha"),
                        EntityField(name="MAIN", value="trunk"),
                        EntityField(name="STATUS", value="active"),
                    ),
                ),
                Entity(
                    name="zeta",
                    fields=(
                        EntityField(name="PATH", value='/srv/a "quoted" \\ path'),
                        EntityField(name="MAIN", value="main"),
                        EntityField(name="ACCEPTANCE", value="make check"),
                        EntityField(name="ACCEPTANCE", value="make lint"),
                        EntityField(name="STATUS", value="paused"),
                    ),
                ),
            ),
        )

    def test_should_read_none_when_no_entity_has_the_type(self):
        # Act
        entities = read_entities(run_process, self.corpus, "PROJECT")

        # Assert
        self.assertEqual(entities, ())
