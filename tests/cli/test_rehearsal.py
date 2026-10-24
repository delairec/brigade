import json
import unittest
from unittest.mock import ANY

from tests.cli.wave_rehearser import ClassCleanupRegistrar, WaveRehearser


class BrigadeRehearsalOfAThreeTaskWaveOnTheFakeClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = WaveRehearser(ClassCleanupRegistrar(cls))
        cls.rehearser.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        cls.rehearser.tick_until_the_wave_is_integrated()

    def test_should_merge_the_three_tasks_into_the_branch_of_the_wave(self):
        # Act
        completed = self.rehearser.run_brigade("wave", "show", "shop_w1", "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "wave": "shop_w1",
                "project": "shop",
                "branch": "integration/shop_w1",
                "started_at": ANY,
                "last_event": "wave.reported",
                "pull_request": ANY,
                "tasks": [
                    {"task": "S1", "state": "merged", "pull_request": ANY, "run": ANY},
                    {"task": "S2", "state": "merged", "pull_request": ANY, "run": ANY},
                    {"task": "S3", "state": "merged", "pull_request": ANY, "run": ANY},
                ],
            },
        )

    def test_should_open_the_integration_pull_request_wave_pr_opened_names(self):
        # Arrange
        opened = self.rehearser.read_events("wave.pr_opened")[0]

        # Act
        pull_request = self.rehearser.read_pull_request(opened["pr"])

        # Assert
        self.assertEqual(opened["wave"], "shop_w1")
        self.assertEqual(pull_request["headRefName"], "integration/shop_w1")
        self.assertEqual(pull_request["baseRefName"], "main")

    def test_should_record_every_run_in_the_ledger(self):
        # Arrange
        runs = self.rehearser.list_finished_runs()

        # Act
        completed = self.rehearser.run_brigade("ledger", "--json")

        # Assert
        self.assertEqual(len(runs), 8)
        self.assertEqual(json.loads(completed.stdout)["runs"], {"outcomes": {"done": 8}, "error_classes": {}})
