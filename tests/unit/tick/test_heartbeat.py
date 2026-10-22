import unittest

from brigade.tick.heartbeat import Heartbeat

HEARTBEAT_DOCUMENT = {
    "schema_version": 1,
    "ts": "2026-10-08T09:00:00Z",
    "duration_ms": 412,
    "actions_applied": 3,
    "actions_failed": 1,
}


class HeartbeatTest(unittest.TestCase):
    def test_should_write_back_the_heartbeat_it_read(self):
        # Act
        document = Heartbeat.from_document(HEARTBEAT_DOCUMENT).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "ts": "2026-10-08T09:00:00Z",
                "duration_ms": 412,
                "actions_applied": 3,
                "actions_failed": 1,
            },
        )
