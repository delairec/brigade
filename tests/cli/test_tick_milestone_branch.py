import unittest
from unittest.mock import ANY

from tests.cli.wave_rehearser import ClassCleanupRegistrar, WaveRehearser

MILESTONE = 'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS active\n'
TASK_TO_DELIVER = (
    'TASK S1\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tTYPE feat\n\tMILESTONE @MILESTONE.M1\n'
)
TASK_DELIVERED = (
    'TASK S1\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tTYPE feat\n\tMILESTONE @MILESTONE.M1\n'
    "\tDELIVERED_BY 7\n"
)
WAVE_BRANCH = "integration/shop_w1"
PULL_REQUEST_OPEN_INTO_MAIN = (
    '{"number": 1, "title": "chore(wave): merge the wave shop_w1 into main",'
    ' "body": "Integrates the wave shop_w1 of @PROJECT.shop into main: @TASK.S1.",'
    f' "headRefName": "{WAVE_BRANCH}", "baseRefName": "main", "state": "OPEN", "reviewDecision": null,'
    ' "author": "octo-build"}'
)
PULL_REQUEST_THAT_DELIVERED_THE_TASK = (
    '{"number": 7, "title": "feat(cart): empty the cart in one click (@TASK.S1)", "body": "Delivers @TASK.S1.",'
    ' "headRefName": "task/shop_w1/S1", "baseRefName": "main", "mergedHead": "main", "state": "MERGED",'
    ' "reviewDecision": null, "author": "octo-build"}'
)
EVENTS_OF_A_WAVE_STARTED_BEFORE_ITS_MILESTONE_HAD_A_BRANCH = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S1"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S1",'
    ' "state": "merged"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "wave.pr_opened", "wave": "shop_w1", "pr": 1,'
    ' "login": "octo-cli"}\n'
)


def prepare_a_wave_of_an_uncut_milestone_open_into_main(rehearser: WaveRehearser) -> None:
    project = rehearser.project
    project.write("corpus/milestones.awawa", MILESTONE)
    project.write("corpus/tasks.awawa", TASK_TO_DELIVER)
    project.track("corpus")
    project.run_git("commit", "--quiet", "-m", "the plan of M1")
    project.run_git("push", "--quiet", "origin", "main")
    project.run_git("checkout", "--quiet", "-b", WAVE_BRANCH)
    project.write("corpus/tasks.awawa", TASK_DELIVERED)
    project.track("corpus")
    project.run_git("commit", "--quiet", "-m", "deliver S1")
    project.run_git("push", "--quiet", "origin", WAVE_BRANCH)
    project.run_git("checkout", "--quiet", "main")
    (rehearser.store / "pulls").mkdir(exist_ok=True)
    (rehearser.store / "pulls" / "1.json").write_text(PULL_REQUEST_OPEN_INTO_MAIN)
    (rehearser.store / "pulls" / "7.json").write_text(PULL_REQUEST_THAT_DELIVERED_THE_TASK)
    (rehearser.state / "ledger").mkdir(parents=True, exist_ok=True)
    ledger = rehearser.state / "ledger" / "2026-10.jsonl"
    ledger.write_text(EVENTS_OF_A_WAVE_STARTED_BEFORE_ITS_MILESTONE_HAD_A_BRANCH)


class BrigadeTickOfAWaveOfAnUncutMilestoneOpenIntoMainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = WaveRehearser(ClassCleanupRegistrar(cls))
        prepare_a_wave_of_an_uncut_milestone_open_into_main(cls.rehearser)
        completed = cls.rehearser.run_brigade("tick", "--once")
        if completed.returncode != 0 or completed.stderr:
            cls.rehearser.registrar.fail(completed.stderr)

    def test_should_record_the_branch_it_cut_for_the_milestone_of_the_wave(self):
        # Act
        events = self.rehearser.read_events()

        # Assert
        self.assertIn(
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "milestone.branch_cut",
                "project": "shop",
                "milestone": "M1",
                "branch": "integration/empty-cart",
                "login": "octo-cli",
            },
            events,
        )

    def test_should_record_the_retarget_of_the_pull_request_of_the_wave_onto_the_branch_of_its_milestone(self):
        # Act
        events = self.rehearser.read_events()

        # Assert
        self.assertIn(
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "wave.pr_retargeted",
                "wave": "shop_w1",
                "pr": 1,
                "base": "integration/empty-cart",
                "login": "octo-cli",
            },
            events,
        )

    def test_should_move_the_pull_request_of_the_wave_onto_the_branch_of_its_milestone(self):
        # Act
        pull_request = self.rehearser.read_pull_request(1)

        # Assert
        self.assertEqual(pull_request["baseRefName"], "integration/empty-cart")
