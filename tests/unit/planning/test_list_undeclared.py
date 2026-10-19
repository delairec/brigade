import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.planning.list_undeclared import list_undeclared
from brigade.planning.read_plan import PlanEntity
from tests.unit.scripted_processes import ScriptedProcesses

TASK_SKELETON = 'TASK B12\n\tTITLE ""\n\t// SPEC ""\n\tWHEN STATUS\n\t\tGATE error\n'


class ListUndeclaredTest(unittest.TestCase):
    def test_should_name_each_field_the_schema_does_not_declare_once(self):
        # Arrange
        processes = ScriptedProcesses()
        processes.answer(("awawa", "new", "TASK", "B12", "/srv/oak"), stdout=TASK_SKELETON)
        processes.answer(("awawa", "new", "TASK", "B13", "/srv/oak"), stdout=TASK_SKELETON)
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
        undeclared = list_undeclared(processes, Path("/srv/oak"), plan)

        # Assert
        self.assertEqual(undeclared, ["the field OWNER of TASK"])

    def test_should_name_a_type_the_schema_does_not_declare(self):
        # Arrange
        processes = ScriptedProcesses()
        processes.answer(("awawa", "new", "EPIC", "E1", "/srv/oak"), exit_code=1)
        plan = (PlanEntity(type="EPIC", entity=Entity(name="E1", fields=(EntityField(name="TITLE", value="x"),))),)

        # Act
        undeclared = list_undeclared(processes, Path("/srv/oak"), plan)

        # Assert
        self.assertEqual(undeclared, ["the type EPIC"])
