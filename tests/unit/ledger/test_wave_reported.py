import unittest

from brigade.ledger.wave_reported import WaveReported


class WaveReportedTest(unittest.TestCase):
    def test_should_read_the_wave_and_the_run_that_reported_it(self):
        # Act
        event = WaveReported.from_document(
            {"event": "wave.reported", "wave": "tidepool_w16", "run": "20261019T090000Z-5c1d2e"}
        )

        # Assert
        self.assertEqual(event, WaveReported(wave="tidepool_w16", run="20261019T090000Z-5c1d2e"))


if __name__ == "__main__":
    unittest.main()
