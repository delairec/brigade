import json
import unittest

from tests.cli.wave_rehearser import ClassCleanupRegistrar, WaveRehearser

MILESTONE_BRANCH = "integration/empty-cart"
FIRST_WAVE = "shop_w1"
FOLLOWING_TASK = (
    'TASK S4\n\tTITLE "Undo emptying the cart"\n\tSTATUS todo\n\tTYPE feat\n'
    "\tMILESTONE @MILESTONE.M1\n\tAFTER @TASK.S1\n"
)


class TickOfAWaveWaitingOnATaskAnEarlierWaveMergedOnTheForgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = WaveRehearser(ClassCleanupRegistrar(cls))
        rehearser = cls.rehearser
        rehearser.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        rehearser.tick_until(lambda: "merged" in rehearser.read_task_states("S1"), "the task S1 was never merged")
        rehearser.run_brigade("project", "pause", "shop")
        cls.push_the_following_task()
        rehearser.tick_until(lambda: rehearser.has_the_wave_closed(FIRST_WAVE), "the first wave never closed")
        rehearser.run_brigade("project", "resume", "shop")
        cls.dry_run = rehearser.run_brigade("tick", "--dry-run", "--json")
        cls.tick = rehearser.run_brigade("tick", "--once")

    @classmethod
    def push_the_following_task(cls) -> None:
        clone = cls.rehearser.store / "amending-clone"
        project = cls.rehearser.project
        project.run_git("clone", "--quiet", "--branch", MILESTONE_BRANCH, str(cls.rehearser.remote), str(clone))
        (clone / "corpus" / "following.awawa").write_text(FOLLOWING_TASK)
        project.run_git("-C", str(clone), "add", "corpus/following.awawa")
        project.run_git("-C", str(clone), "commit", "--quiet", "-m", "docs: plan the task that follows S1")
        project.run_git("-C", str(clone), "push", "--quiet", "origin", MILESTONE_BRANCH)

    def read_the_local_and_forge_heads_of_the_milestone_branch(self) -> tuple[str, str]:
        project = self.rehearser.project
        local_head = project.run_git("rev-parse", MILESTONE_BRANCH)
        return local_head, project.run_git("--git-dir", str(self.rehearser.remote), "rev-parse", MILESTONE_BRANCH)

    def test_should_leave_the_local_branch_of_the_milestone_behind_the_forge(self):
        # Act
        local_head, remote_head = self.read_the_local_and_forge_heads_of_the_milestone_branch()

        # Assert
        self.assertNotEqual(local_head, remote_head)

    def test_should_plan_the_start_of_the_wave_of_the_task_at_a_dry_run(self):
        # Act
        document = json.loads(self.dry_run.stdout)

        # Assert
        self.assertIn({"project": "shop", "milestone": "M1"}, document["plan"])

    def test_should_offer_the_task_as_the_candidate_of_that_wave_at_a_dry_run(self):
        # Act
        document = json.loads(self.dry_run.stdout)

        # Assert
        self.assertEqual(document["snapshot"]["projects"][0]["candidates"], [{"milestone": "M1", "tasks": ["S4"]}])

    def test_should_launch_the_task_at_the_next_tick_with_no_manual_step(self):
        # Act
        states = self.rehearser.read_task_states("S4")

        # Assert
        self.assertIn("running", states)
