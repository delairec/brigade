import unittest
from pathlib import Path

from brigade.waves.compose_milestone_title import MilestoneTitleDemand, compose_milestone_title
from tests.unit.scripted_processes import ScriptedProcesses

HEAD_TREE = Path("/cache/refs/oak/8885daa")
PULL_REQUEST_TITLES = {
    341: "feat(tick): open the pull request of a milestone (@TASK.B17)",
    352: "fix(tick): name the base of a rebuild (@TASK.B21)",
    298: "docs(wiki): describe the tick (@TASK.B12)",
}


class ComposeMilestoneTitleTest(unittest.TestCase):
    def test_should_title_the_tasks_of_the_milestone_implemented_at_the_head_by_the_titles_of_their_pull_requests(
        self,
    ):
        # Arrange
        awawa = ScriptedProcesses()
        awawa.answer_entities(
            HEAD_TREE,
            "TASK",
            {
                "B12": (
                    ("TYPE", "docs"),
                    ("COMPONENT", "wiki"),
                    ("MILESTONE", "@MILESTONE.M5"),
                    ("DELIVERED_BY", "298"),
                ),
                "B17": (
                    ("TYPE", "feat"),
                    ("COMPONENT", "tick"),
                    ("MILESTONE", "@MILESTONE.M6"),
                    ("DELIVERED_BY", "341"),
                ),
                "B21": (
                    ("TYPE", "fix"),
                    ("COMPONENT", "tick"),
                    ("MILESTONE", "@MILESTONE.M6"),
                    ("DELIVERED_BY", "352"),
                ),
            },
            ("STATUS==implemented",),
        )
        demand = MilestoneTitleDemand(
            run_process=awawa, root=HEAD_TREE, milestone="M6", read_pull_request_title=PULL_REQUEST_TITLES.__getitem__
        )

        # Act
        title = compose_milestone_title(demand)

        # Assert
        self.assertEqual(
            title,
            "feat(tick): open the pull request of a milestone; name the base of a rebuild (M6, @TASK.B17, @TASK.B21)",
        )


if __name__ == "__main__":
    unittest.main()
