import unittest
from pathlib import Path

from brigade.waves.compose_milestone_title import MilestoneTitleDemand, compose_milestone_title
from tests.unit.scripted_processes import ScriptedProcesses

HEAD_TREE = Path("/cache/refs/oak/8885daa")
IMPLEMENTED_TASKS = {
    "B12": (("TYPE", "docs"), ("COMPONENT", "wiki"), ("MILESTONE", "@MILESTONE.M5")),
    "B17": (("TYPE", "feat"), ("COMPONENT", "tick"), ("MILESTONE", "@MILESTONE.M6")),
    "B21": (("TYPE", "fix"), ("COMPONENT", "tick"), ("MILESTONE", "@MILESTONE.M6")),
}


def create_awawa(milestone_fields: tuple[tuple[str, str], ...]) -> ScriptedProcesses:
    awawa = ScriptedProcesses()
    awawa.answer_entity(HEAD_TREE, "MILESTONE", "M6", milestone_fields)
    awawa.answer_entities(HEAD_TREE, "TASK", IMPLEMENTED_TASKS, ("STATUS==implemented",))
    return awawa


class ComposeMilestoneTitleTest(unittest.TestCase):
    def test_should_title_the_milestone_by_its_subject_typed_and_scoped_by_its_tasks_implemented_at_the_head(self):
        # Arrange
        awawa = create_awawa(
            (("TITLE", "Hardening"), ("SUBJECT", "harden the tick against moved heads"), ("STATUS", "active"))
        )
        demand = MilestoneTitleDemand(run_process=awawa, root=HEAD_TREE, milestone="M6")

        # Act
        title = compose_milestone_title(demand)

        # Assert
        self.assertEqual(title, "feat(tick): harden the tick against moved heads (M6)")

    def test_should_take_the_title_of_the_milestone_in_place_of_a_missing_subject(self):
        # Arrange
        awawa = create_awawa((("TITLE", "Hardening"), ("STATUS", "active")))
        demand = MilestoneTitleDemand(run_process=awawa, root=HEAD_TREE, milestone="M6")

        # Act
        title = compose_milestone_title(demand)

        # Assert
        self.assertEqual(title, "feat(tick): Hardening (M6)")


if __name__ == "__main__":
    unittest.main()
