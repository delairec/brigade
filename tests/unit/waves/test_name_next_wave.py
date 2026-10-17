import unittest

from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.name_next_wave import name_next_wave


class NameNextWaveTest(unittest.TestCase):
    def test_should_number_the_first_wave_of_a_project_1(self):
        # Arrange
        no_events = ()

        # Act
        name = name_next_wave("shop", no_events)

        # Assert
        self.assertEqual(name, "shop_w1")

    def test_should_number_a_wave_one_above_the_highest_wave_of_its_project(self):
        # Arrange
        events = (
            WaveStarted(wave="shop_w10", project="shop", branch="integration/M1-empty-cart", tasks=("S3",)),
            WaveStarted(wave="cafe_w12", project="cafe", branch="integration/M1-receipt", tasks=("C1",)),
            WaveStarted(wave="shop_w9", project="shop", branch="integration/M2-undo", tasks=("S5",)),
            TaskState(wave="shop_w10", task="S3", state="running"),
        )

        # Act
        name = name_next_wave("shop", events)

        # Assert
        self.assertEqual(name, "shop_w11")
