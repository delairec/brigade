import unittest

from brigade.ledger.run_finished import RunFinished
from brigade.system.token_usage import TokenUsage

RUN_OF_A_WAVE_WITH_ITS_MEASURES = {
    "run": "20261008T090000Z-b74a01",
    "segment": 2,
    "procedure": "awawa-task",
    "slot": "build",
    "role": "builder",
    "client": "claude-code",
    "project": "tidepool",
    "session": "session-b74",
    "main_steps": 40,
    "total_steps": 52,
    "duration_ms": 61000,
    "usage": {
        "input_tokens": 1200,
        "output_tokens": 340,
        "cache_creation_input_tokens": 50,
        "cache_read_input_tokens": 9000,
    },
    "outcome": "failed",
    "error_class": "rate_limit",
    "exit": 1,
    "wave": "tp/16",
    "task": "TP146",
    "nulls": {},
    "steps_to_first_edit": 12,
    "oversized_output_steps": 1,
    "cost_usd": 3.63,
}
RUN_REPORTING_NOTHING = {
    "run": "20261008T090000Z-b74a02",
    "segment": 1,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "client": "fake",
    "project": None,
    "session": None,
    "main_steps": None,
    "total_steps": None,
    "duration_ms": 1500000,
    "usage": None,
    "outcome": "wall_limit",
    "error_class": None,
    "exit": None,
    "wave": None,
    "task": None,
    "nulls": {"project": "no project given"},
}


class RunFinishedTest(unittest.TestCase):
    def test_should_write_back_a_run_carrying_every_field_its_measures_and_its_cost(self):
        # Act
        document = RunFinished.from_document(RUN_OF_A_WAVE_WITH_ITS_MEASURES).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "run": "20261008T090000Z-b74a01",
                "segment": 2,
                "procedure": "awawa-task",
                "slot": "build",
                "role": "builder",
                "client": "claude-code",
                "project": "tidepool",
                "session": "session-b74",
                "main_steps": 40,
                "total_steps": 52,
                "duration_ms": 61000,
                "usage": {
                    "input_tokens": 1200,
                    "output_tokens": 340,
                    "cache_creation_input_tokens": 50,
                    "cache_read_input_tokens": 9000,
                },
                "outcome": "failed",
                "error_class": "rate_limit",
                "exit": 1,
                "wave": "tp/16",
                "task": "TP146",
                "nulls": {},
                "steps_to_first_edit": 12,
                "oversized_output_steps": 1,
                "cost_usd": 3.63,
            },
        )

    def test_should_write_back_a_run_whose_nullable_fields_are_null_and_whose_measures_and_cost_are_absent(self):
        # Act
        document = RunFinished.from_document(RUN_REPORTING_NOTHING).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "run": "20261008T090000Z-b74a02",
                "segment": 1,
                "procedure": "deliver",
                "slot": "build",
                "role": "builder",
                "client": "fake",
                "project": None,
                "session": None,
                "main_steps": None,
                "total_steps": None,
                "duration_ms": 1500000,
                "usage": None,
                "outcome": "wall_limit",
                "error_class": None,
                "exit": None,
                "wave": None,
                "task": None,
                "nulls": {"project": "no project given"},
            },
        )

    def test_should_read_the_usage_as_a_token_usage(self):
        # Act
        finished = RunFinished.from_document(RUN_OF_A_WAVE_WITH_ITS_MEASURES)

        # Assert
        self.assertEqual(
            finished.usage,
            TokenUsage(
                input_tokens=1200,
                output_tokens=340,
                cache_creation_input_tokens=50,
                cache_read_input_tokens=9000,
            ),
        )
