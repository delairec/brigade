import unittest
from datetime import UTC, datetime

from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.read_wave_pause import WavePause, read_wave_pause


class ReadWavePauseTest(unittest.TestCase):
    def test_should_read_the_last_pause_of_the_wave_with_the_instant_it_resumes_at(self):
        # Arrange
        events = (
            WaveStarted(wave="oak_w1", project="oak", branch="integration/F0-parser", tasks=("B12",)),
            WavePaused(wave="oak_w1", reason="forge account", resume_at=None),
            WaveResumed(wave="oak_w1", reason="forge account"),
            WavePaused(wave="oak_w1", reason="quota", resume_at="2026-10-19T12:00:00+00:00"),
            WaveResumed(wave="oak_w2", reason="quota"),
        )

        # Act
        pause = read_wave_pause(events, "oak_w1")

        # Assert
        self.assertEqual(pause, WavePause(reason="quota", resume_at=datetime(2026, 10, 19, 12, 0, tzinfo=UTC)))

    def test_should_find_no_pause_once_the_wave_resumed(self):
        # Arrange
        events = (
            WavePaused(wave="oak_w1", reason="quota", resume_at="2026-10-19T12:00:00+00:00"),
            WaveResumed(wave="oak_w1", reason="quota"),
        )

        # Act
        pause = read_wave_pause(events, "oak_w1")

        # Assert
        self.assertIsNone(pause)


class WavePauseDocumentTest(unittest.TestCase):
    def test_should_present_the_instant_a_pause_ends_at_as_an_utc_instant(self):
        for pause, expected in [
            (
                WavePause(reason="quota", resume_at=datetime(2026, 10, 19, 12, 0, tzinfo=UTC)),
                {"reason": "quota", "resume_at": "2026-10-19T12:00:00Z"},
            ),
            (WavePause(reason="forge account", resume_at=None), {"reason": "forge account", "resume_at": None}),
        ]:
            with self.subTest(pause=pause):
                # Act
                document = pause.to_document()

                # Assert
                self.assertEqual(document, expected)
