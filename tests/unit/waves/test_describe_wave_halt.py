import unittest
from datetime import UTC, datetime

from brigade.waves.describe_wave_halt import describe_wave_halt
from brigade.waves.read_wave_pause import WavePause


class DescribeWaveHaltTest(unittest.TestCase):
    def test_should_say_whether_a_wave_is_blocked_until_its_resume_or_parked_until_the_user_resumes_it(self):
        for case, halt, expected in [
            (
                "blocked",
                WavePause(reason="the quota of claude is spent", resume_at=datetime(2026, 10, 6, 13, 0, tzinfo=UTC)),
                "wave shop_w1 blocked until 2026-10-06T13:00:00Z: the quota of claude is spent",
            ),
            (
                "parked",
                WavePause(reason="the forge account is unavailable", resume_at=None),
                "wave shop_w1 parked: the forge account is unavailable; it waits for brigade wave resume shop_w1",
            ),
        ]:
            with self.subTest(case=case):
                # Act
                line = describe_wave_halt("shop_w1", halt)

                # Assert
                self.assertEqual(line, expected)


if __name__ == "__main__":
    unittest.main()
