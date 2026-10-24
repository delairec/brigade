import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.planning.read_plan import PlanEntity, read_plan

PLAN_FILE = Path("/srv/runs/r1/plan.awawa")
DOCUMENTS = {
    (PLAN_FILE, ("show", "/srv/runs/r1/plan.awawa")): {
        "entities": [{"type": "MILESTONE", "name": "F1"}, {"type": "TASK", "name": "B20"}]
    },
    (PLAN_FILE, ("show", "@MILESTONE.F1")): {"fields": [{"name": "TITLE", "atoms": ['"the "', '"printer"']}]},
    (PLAN_FILE, ("show", "@TASK.B20")): {"fields": [{"name": "MILESTONE", "atoms": ["@MILESTONE.F1"]}]},
}


def read_awawa_file_document(file: Path, arguments: tuple[str, ...]) -> dict:
    return DOCUMENTS[(file, arguments)]


class ReadPlanTest(unittest.TestCase):
    def test_should_read_each_entity_of_the_plan_file_with_its_fields(self):
        # Act
        plan = read_plan(read_awawa_file_document, PLAN_FILE)

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

    def test_should_keep_in_a_value_the_backslash_awawa_keeps(self):
        # Arrange
        documents = {
            (PLAN_FILE, ("show", "/srv/runs/r1/plan.awawa")): {"entities": [{"type": "MILESTONE", "name": "F1"}]},
            (PLAN_FILE, ("show", "@MILESTONE.F1")): {
                "fields": [{"name": "TITLE", "atoms": [r'"the \.awawa printer"']}]
            },
        }

        # Act
        plan = read_plan(lambda file, arguments: documents[(file, arguments)], PLAN_FILE)

        # Assert
        self.assertEqual(plan[0].entity.fields, (EntityField(name="TITLE", value=r"the \.awawa printer"),))
