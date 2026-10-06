import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.tick.read_heartbeat import read_heartbeat


class ReadHeartbeat(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.heartbeat = Path(self.root.name) / "tick.json"

    def tearDown(self):
        self.root.cleanup()

    def test_should_read_no_tick_before_the_first_one(self):
        # Act
        last_tick = read_heartbeat(self.heartbeat)

        # Assert
        self.assertIsNone(last_tick)

    def test_should_read_the_last_tick(self):
        # Arrange
        self.heartbeat.write_text('{"schema_version": 1, "ts": "2026-10-06T12:00:00Z", "duration_ms": 4, "actions_applied": 2}')

        # Act
        last_tick = read_heartbeat(self.heartbeat)

        # Assert
        self.assertEqual(
            last_tick, {"schema_version": 1, "ts": "2026-10-06T12:00:00Z", "duration_ms": 4, "actions_applied": 2}
        )

    def test_should_refuse_a_file_that_is_not_a_heartbeat_naming_it(self):
        rows = [
            (
                "an unknown version",
                '{"schema_version": 2, "ts": "2026-10-06T12:00:00Z", "duration_ms": 4, "actions_applied": 0}',
                "schema_version is 2, not one of 1",
            ),
            ("a missing key", '{"schema_version": 1, "ts": "2026-10-06T12:00:00Z"}', "lacks the key duration_ms"),
            ("no JSON", "{", "not a JSON document"),
        ]
        for case, content, expected_problem in rows:
            with self.subTest(case=case):
                # Arrange
                self.heartbeat.write_text(content)

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    read_heartbeat(self.heartbeat)

                # Assert
                self.assertEqual(str(refusal.exception), f"{self.heartbeat} is not a heartbeat: {expected_problem}")
