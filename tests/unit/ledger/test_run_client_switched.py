import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.run_client_switched import RunClientSwitched


class RunClientSwitchedTest(unittest.TestCase):
    def test_should_read_the_switch_of_a_run_with_the_client_and_the_model_it_left_and_took(self):
        # Act
        event = RunClientSwitched.from_document(
            {
                "event": "run.client_switched",
                "run": "20261019T090000Z-a1b2c3",
                "client_left": "claude-code",
                "model_left": "opus",
                "client_taken": "vibe",
                "model_taken": "devstral",
                "reason": "rate_limit",
            }
        )

        # Assert
        self.assertEqual(
            event,
            RunClientSwitched(
                run="20261019T090000Z-a1b2c3",
                client_left="claude-code",
                model_left="opus",
                client_taken="vibe",
                model_taken="devstral",
                reason="rate_limit",
            ),
        )

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("run.client_switched")

        # Assert
        self.assertIs(declared, RunClientSwitched)
