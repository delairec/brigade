import json
import unittest
from unittest.mock import ANY

from tests.cli.forgeless_wave_rehearser import MILESTONE_BRANCH
from tests.cli.fresh_account_rehearser import FreshAccountWaveRehearser
from tests.cli.wave_rehearser import ClassCleanupRegistrar

FORGE_OF_NO_PROJECT = {
    "name": "forge",
    "kind": "optional",
    "state": "ok",
    "detail": "no registered project on a forge",
    "fallback": "local mode without a forge",
}


class BrigadeOnAFreshAccountFromTheBuiltArchiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = FreshAccountWaveRehearser(ClassCleanupRegistrar(cls))
        cls.rehearser.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        cls.rehearser.tick_until_the_milestone_is_reported()

    def test_should_initialise_the_operational_corpus(self):
        # Act
        completed = self.rehearser.init

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_should_pass_doctor_with_each_optional_item_on_its_fallback_but_the_forge(self):
        # Act
        completed = self.rehearser.doctor_before_the_project

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"],
            [
                {"name": "python", "kind": "prerequisite", "state": "ok", "detail": ANY, "fallback": None},
                {"name": "git", "kind": "prerequisite", "state": "ok", "detail": ANY, "fallback": None},
                {"name": "awawa", "kind": "prerequisite", "state": "ok", "detail": ANY, "fallback": None},
                {
                    "name": "client",
                    "kind": "prerequisite",
                    "state": "ok",
                    "detail": "fake: no client executable",
                    "fallback": None,
                },
                {
                    "name": "scheduler",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "no user systemd instance",
                    "fallback": "a cron line, or brigade tick --loop",
                },
                FORGE_OF_NO_PROJECT,
                {
                    "name": "awawa-web",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "not on PATH",
                    "fallback": "the dashboard's corpus view only",
                },
                {
                    "name": "instructions",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "none configured",
                    "fallback": "built-in roles and no instructions package",
                },
                {
                    "name": "steps",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "fake counts no steps: the budget is held on the clock and the run cut at its limit",
                    "fallback": "the wall-time limit of each run",
                },
            ],
        )

    def test_should_keep_the_forge_ok_once_the_sandbox_of_forge_none_is_registered(self):
        # Act
        completed = self.rehearser.doctor_after_the_project

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["items"][5], FORGE_OF_NO_PROJECT)

    def test_should_merge_the_task_of_a_one_task_wave_into_the_branch_of_its_milestone(self):
        # Act
        delivered = self.rehearser.project.run_git("show", f"{MILESTONE_BRANCH}:delivered-S1.txt")

        # Assert
        self.assertEqual(delivered, "S1\n")
