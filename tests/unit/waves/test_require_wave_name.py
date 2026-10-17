import unittest

from brigade.errors import BrigadeError
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.require_wave_name import require_wave_name

WAVE_BRANCH = "integration/M1-empty-cart"
RUNNING_REQUEST = {"name": "shop_1", "project": "shop", "status": "running", "milestone": "M1", "branch": WAVE_BRANCH}


class RequireWaveNameTest(unittest.TestCase):
    def test_should_name_the_wave_started_on_the_branch_of_the_request(self):
        # Arrange
        events = (WaveStarted(wave="shop_w1", project="shop", branch=WAVE_BRANCH, tasks=("S3",)),)

        # Act
        name = require_wave_name(events, RUNNING_REQUEST)

        # Assert
        self.assertEqual(name, "shop_w1")

    def test_should_refuse_a_request_whose_branch_no_wave_started_names(self):
        # Arrange
        no_events = ()

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            require_wave_name(no_events, RUNNING_REQUEST)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"no wave.started of @PROJECT.shop names {WAVE_BRANCH}, the BRANCH of @REQUEST.shop_1",
        )
