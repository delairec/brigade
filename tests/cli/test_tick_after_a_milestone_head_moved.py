import json
import unittest

from tests.cli.wave_rehearser import ClassCleanupRegistrar, WaveRehearser

MILESTONE_BRANCH = "integration/empty-cart"
MILESTONE_PULL_REQUEST = 5


class TickAfterTheHeadOfAMilestonePullRequestMovedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = WaveRehearser(ClassCleanupRegistrar(cls))
        cls.rehearser.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        cls.rehearser.tick_until_the_milestone_is_reported()

    def _retitle_by_hand(self, title: str) -> None:
        pull = self.rehearser.store / "pulls" / f"{MILESTONE_PULL_REQUEST}.json"
        pull.write_text(json.dumps({**json.loads(pull.read_text()), "title": title}))

    def _push_a_commit_on_the_milestone_branch(self) -> None:
        clone = self.rehearser.store / "amending-clone"
        project = self.rehearser.project
        project.run_git("clone", "--quiet", "--branch", MILESTONE_BRANCH, str(self.rehearser.remote), str(clone))
        project.run_git("-C", str(clone), "commit", "--quiet", "--allow-empty", "-m", "docs: amend the milestone")
        project.run_git("-C", str(clone), "push", "--quiet", "origin", MILESTONE_BRANCH)

    def test_should_retitle_the_pull_request_of_the_milestone_by_what_its_head_delivers_once_its_branch_moved(self):
        # Arrange
        self._retitle_by_hand("chore(milestone): merge the milestone M1 into main")
        self._push_a_commit_on_the_milestone_branch()

        # Act
        self.rehearser.run_brigade("tick", "--once")

        # Assert
        self.assertEqual(
            self.rehearser.read_pull_request(MILESTONE_PULL_REQUEST)["title"],
            "feat: deliver S1; deliver S2; deliver S3 (M1, @TASK.S1, @TASK.S2, @TASK.S3)",
        )
