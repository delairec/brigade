import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.planning.list_undeclared import list_undeclared
from brigade.planning.read_plan import PlanEntity

ROOT = Path("/srv/oak")
TEMPLATES = {
    (ROOT, "TASK", "B12"): 'TASK B12\n\tTITLE ""\n\t// SPEC ""\n\tWHEN STATUS\n\t\tGATE error\n',
    (ROOT, "TASK", "B13"): 'TASK B13\n\tTITLE ""\n\t// SPEC ""\n\tWHEN STATUS\n\t\tGATE error\n',
    (ROOT, "EPIC", "E1"): None,
}


def read_entity_template(root: Path, entity_type: str, name: str) -> str | None:
    return TEMPLATES[(root, entity_type, name)]


class ListUndeclaredTest(unittest.TestCase):
    def test_should_name_each_field_the_schema_does_not_declare_once(self):
        # Arrange
        plan = (
            PlanEntity(
                type="TASK",
                entity=Entity(
                    name="B12",
                    fields=(
                        EntityField(name="TITLE", value="the parser"),
                        EntityField(name="SPEC", value="parses"),
                        EntityField(name="OWNER", value="ada"),
                    ),
                ),
            ),
            PlanEntity(type="TASK", entity=Entity(name="B13", fields=(EntityField(name="OWNER", value="bob"),))),
        )

        # Act
        undeclared = list_undeclared(read_entity_template, ROOT, plan)

        # Assert
        self.assertEqual(undeclared, ["the field OWNER of TASK"])

    def test_should_name_a_type_the_schema_does_not_declare(self):
        # Arrange
        plan = (PlanEntity(type="EPIC", entity=Entity(name="E1", fields=(EntityField(name="TITLE", value="x"),))),)

        # Act
        undeclared = list_undeclared(read_entity_template, ROOT, plan)

        # Assert
        self.assertEqual(undeclared, ["the type EPIC"])
