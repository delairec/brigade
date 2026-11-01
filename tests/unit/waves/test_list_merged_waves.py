import unittest

from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.list_merged_waves import list_merged_waves
from brigade.waves.merged_wave import MergedWave

TASKS_OF_M4 = {"T7", "T9"}
STARTED_W16 = WaveStarted(wave="tidepool_w16", project="tidepool", branch="integration/w16", tasks=("T7",))
STARTED_W17 = WaveStarted(wave="tidepool_w17", project="tidepool", branch="integration/w17", tasks=("T9",))
STARTED_W18_OF_ANOTHER_MILESTONE = WaveStarted(
    wave="tidepool_w18", project="tidepool", branch="integration/w18", tasks=("T11",)
)
STARTED_IN_ANOTHER_PROJECT = WaveStarted(wave="reef_w3", project="reef", branch="integration/w3", tasks=("T7",))


class ListMergedWavesTest(unittest.TestCase):
    def test_should_list_the_closed_waves_of_the_milestone_with_their_pull_request_in_the_order_they_started(self):
        # Arrange
        events = (
            STARTED_W16,
            STARTED_W17,
            STARTED_W18_OF_ANOTHER_MILESTONE,
            STARTED_IN_ANOTHER_PROJECT,
            WaveClosed(wave="tidepool_w17", pr=63),
            WaveClosed(wave="tidepool_w16", pr=57),
            WaveClosed(wave="tidepool_w18", pr=70),
            WaveClosed(wave="reef_w3", pr=12),
        )

        # Act
        merged = list_merged_waves(events, "tidepool", TASKS_OF_M4)

        # Assert
        self.assertEqual(merged, (MergedWave(wave="tidepool_w16", pr=57), MergedWave(wave="tidepool_w17", pr=63)))

    def test_should_leave_out_a_wave_of_the_milestone_still_open(self):
        # Arrange
        events = (STARTED_W16, STARTED_W17, WaveClosed(wave="tidepool_w16", pr=57))

        # Act
        merged = list_merged_waves(events, "tidepool", TASKS_OF_M4)

        # Assert
        self.assertEqual(merged, (MergedWave(wave="tidepool_w16", pr=57),))
