from datetime import UTC, datetime

from brigade.processes.locate_trails import Trail, locate_trails
from tests.unit.processes.state_with_trails import StateWithTrailsTestCase


class LocateTrailsTest(StateWithTrailsTestCase):
    def test_should_locate_the_trails_of_runs_ticks_and_commands_named_by_an_instant(self):
        # Act
        trails = locate_trails(self.state_root)

        # Assert
        self.assertEqual(
            trails,
            [
                Trail(
                    kind="run",
                    id="20261010T090000Z-b86a01",
                    instant=datetime(2026, 10, 10, 9, 0, tzinfo=UTC),
                    path=self.state_root / "runs/20261010T090000Z-b86a01/processes.jsonl",
                ),
                Trail(
                    kind="tick",
                    id="20261010T100000Z",
                    instant=datetime(2026, 10, 10, 10, 0, tzinfo=UTC),
                    path=self.state_root / "ticks/20261010T100000Z.jsonl",
                ),
                Trail(
                    kind="command",
                    id="20261010T080000Z-ab12",
                    instant=datetime(2026, 10, 10, 8, 0, tzinfo=UTC),
                    path=self.state_root / "commands/20261010T080000Z-ab12.jsonl",
                ),
            ],
        )
