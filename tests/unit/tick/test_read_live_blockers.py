import json
import unittest
from pathlib import Path

from brigade.tick.read_live_blockers import read_live_blockers
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

INCOMING = [
    {"from": {"type": "OPEN_QUESTION", "name": "Q1", "status": "open"}, "field_path": ["BLOCKS"]},
    {"from": {"type": "OPEN_QUESTION", "name": "Q2", "status": "closed"}, "field_path": ["BLOCKS"]},
    {"from": {"type": "DECISION", "name": "D1", "status": "ratified"}, "field_path": ["CITES"]},
]
QUESTION_SCHEMA = {
    "fields": [
        {
            "name": "FIELD",
            "atoms": ["BLOCKS", "reference"],
            "fields": [{"name": "CONVERSE", "atoms": ["BLOCKED_BY"], "fields": []}],
        },
        {"name": "WHEN", "atoms": ["STATUS", "open"], "fields": [{"name": "GATE", "atoms": ["error"], "fields": []}]},
        {
            "name": "WHEN",
            "atoms": ["STATUS", "closed"],
            "fields": [{"name": "GATE", "atoms": ["suppressed"], "fields": []}],
        },
    ]
}
DECISION_SCHEMA = {"fields": [{"name": "FIELD", "atoms": ["CITES", "reference"], "fields": []}]}


class ReadLiveBlockersTest(unittest.TestCase):
    def test_should_keep_the_entities_blocking_the_task_through_a_field_whose_status_still_gates(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {
                ("awawa", "refs", "@TASK.B1", "--json", "/srv/shop"): ProcessAnswer(
                    stdout=json.dumps({"incoming": INCOMING})
                ),
                ("awawa", "show", "OPEN_QUESTION", "--json", "/srv/shop"): ProcessAnswer(
                    stdout=json.dumps(QUESTION_SCHEMA)
                ),
                ("awawa", "show", "DECISION", "--json", "/srv/shop"): ProcessAnswer(stdout=json.dumps(DECISION_SCHEMA)),
            }
        )

        # Act
        blockers = read_live_blockers(awawa, Path("/srv/shop"), "B1")

        # Assert
        self.assertEqual(blockers, ("OPEN_QUESTION.Q1",))
