import unittest

from brigade.ledger.wave_paused import WavePaused


class WavePausedTest(unittest.TestCase):
    def test_should_read_the_pause_of_a_wave_on_the_quota_until_its_resume(self):
        # Act
        event = WavePaused.from_document(
            {"event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": "2026-10-19T15:00:00Z"}
        )

        # Assert
        self.assertEqual(event, WavePaused(wave="tidepool_w16", reason="quota", resume_at="2026-10-19T15:00:00Z"))

    def test_should_write_the_pause_of_a_wave_on_the_forge_account_with_no_resume(self):
        # Arrange
        event = WavePaused(wave="tidepool_w16", reason="forge_account", resume_at=None)

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "tidepool_w16", "reason": "forge_account", "resume_at": None})
