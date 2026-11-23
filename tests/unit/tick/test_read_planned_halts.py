import unittest
from datetime import UTC, datetime

from brigade.tick.actions import PauseWave
from brigade.tick.build_snapshot import Snapshot, WaveFacts
from brigade.tick.read_planned_halts import read_planned_halts
from brigade.waves.read_wave_pause import WavePause

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
HELD_PARK = WavePause(reason="forge_account", resume_at=None)


class ReadPlannedHaltsTest(unittest.TestCase):
    def test_should_read_the_halt_each_wave_holds_or_the_plan_gives_it_in_the_round(self):
        # Arrange
        snapshot = Snapshot(
            now=NOW,
            waves=(
                WaveFacts(project="shop", wave="shop_w1", pause=HELD_PARK),
                WaveFacts(project="shop", wave="shop_w2"),
                WaveFacts(project="shop", wave="shop_w3"),
            ),
        )
        actions = (
            PauseWave(wave="shop_w1", reason="quota", resume_at="2026-10-06T13:00:00Z"),
            PauseWave(wave="shop_w2", reason="quota", resume_at="2026-10-06T13:00:00Z"),
            PauseWave(wave="shop_w3", reason="client_login", resume_at=None),
        )

        # Act
        halts = read_planned_halts(snapshot, actions)

        # Assert
        self.assertEqual(
            halts,
            {
                "shop_w1": WavePause(reason="forge_account", resume_at=None),
                "shop_w2": WavePause(reason="quota", resume_at=datetime(2026, 10, 6, 13, 0, tzinfo=UTC)),
                "shop_w3": WavePause(reason="client_login", resume_at=None),
            },
        )


if __name__ == "__main__":
    unittest.main()
