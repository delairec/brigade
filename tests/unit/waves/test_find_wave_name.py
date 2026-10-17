import unittest

from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.find_wave_name import find_wave_name

WAVE_BRANCH = "integration/M1-empty-cart"


class FindWaveNameTest(unittest.TestCase):
    def test_should_name_the_wave_started_by_the_project_on_the_branch(self):
        # Arrange
        events = (
            WaveStarted(wave="cafe_w1", project="cafe", branch=WAVE_BRANCH, tasks=("C1",)),
            WaveStarted(wave="shop_w1", project="shop", branch=WAVE_BRANCH, tasks=("S3",)),
            WaveStarted(wave="shop_w2", project="shop", branch="integration/M2-undo", tasks=("S5",)),
            TaskState(wave="shop_w2", task="S5", state="running"),
        )

        # Act
        name = find_wave_name(events, "shop", WAVE_BRANCH)

        # Assert
        self.assertEqual(name, "shop_w1")

    def test_should_name_no_wave_when_no_wave_of_the_project_started_on_the_branch(self):
        # Arrange
        events = (WaveStarted(wave="cafe_w1", project="cafe", branch=WAVE_BRANCH, tasks=("C1",)),)

        # Act
        name = find_wave_name(events, "shop", WAVE_BRANCH)

        # Assert
        self.assertIsNone(name)
