import unittest

from brigade.ledger.wave_pr_described import WavePrDescribed
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.waves.find_wave_described_head import find_wave_described_head

NO_EVENT = ()


class FindWaveDescribedHeadTest(unittest.TestCase):
    def test_should_find_the_head_of_the_last_description_of_the_pull_request_of_the_wave(self):
        # Arrange
        events = (
            WavePrOpened(wave="tidepool_w16", pr=77, login="tidepool-cli"),
            WavePrDescribed(wave="tidepool_w16", pr=77, head="c4a7413f", login="tidepool-cli"),
            WavePrDescribed(wave="tidepool_w16", pr=77, head="9010166d", login="tidepool-cli"),
        )

        # Act
        head = find_wave_described_head(events, "tidepool_w16", 77)

        # Assert
        self.assertEqual(head, "9010166d")

    def test_should_find_none(self):
        for case, events in [
            ("no description", NO_EVENT),
            (
                "a description of another wave",
                (WavePrDescribed(wave="tidepool_w17", pr=77, head="c4a7413f", login=None),),
            ),
            (
                "a description of another pull request of the wave",
                (WavePrDescribed(wave="tidepool_w16", pr=76, head="c4a7413f", login=None),),
            ),
        ]:
            with self.subTest(case=case):
                # Act
                head = find_wave_described_head(events, "tidepool_w16", 77)

                # Assert
                self.assertIsNone(head)


if __name__ == "__main__":
    unittest.main()
