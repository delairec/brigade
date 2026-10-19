import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.planning.read_plan import PlanEntity, read_plan
from tests.unit.scripted_processes import ScriptedProcesses


class ReadPlanTest(unittest.TestCase):
    def test_should_read_each_entity_of_the_plan_file_with_its_fields(self):
        # Arrange
        processes = ScriptedProcesses()
        plan_file = "/srv/runs/r1/plan.awawa"
        processes.answer_json(
            ("awawa", "show", plan_file, "--json", plan_file),
            {"entities": [{"type": "MILESTONE", "name": "F1"}, {"type": "TASK", "name": "B20"}]},
        )
        processes.answer_json(
            ("awawa", "show", "@MILESTONE.F1", "--json", plan_file),
            {"fields": [{"name": "TITLE", "atoms": ['"the "', '"printer"']}]},
        )
        processes.answer_json(
            ("awawa", "show", "@TASK.B20", "--json", plan_file),
            {"fields": [{"name": "MILESTONE", "atoms": ["@MILESTONE.F1"]}]},
        )

        # Act
        plan = read_plan(processes, Path(plan_file))

        # Assert
        self.assertEqual(
            plan,
            (
                PlanEntity(
                    type="MILESTONE", entity=Entity(name="F1", fields=(EntityField(name="TITLE", value="the printer"),))
                ),
                PlanEntity(
                    type="TASK",
                    entity=Entity(name="B20", fields=(EntityField(name="MILESTONE", value="@MILESTONE.F1"),)),
                ),
            ),
        )
