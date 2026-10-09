import unittest

from brigade.system.parse_result_answer import ParseResultAnswer

RESULT_OF_A_RATE_LIMITED_RUN = {
    "schema_version": 1,
    "outcome": "failed",
    "steps": 31,
    "usage": {
        "input_tokens": 1200,
        "output_tokens": 340,
        "cache_creation_input_tokens": 50,
        "cache_read_input_tokens": 9000,
    },
    "session_id": "session-b74",
    "duration_ms": 61000,
    "cost_usd": 1.27,
    "error_class": "rate_limit",
    "reset": {"hour": "3pm", "timezone": "Europe/Paris"},
    "message": "usage limit reached",
}
RESULT_REPORTING_NOTHING = {
    "schema_version": 1,
    "outcome": "done",
    "steps": None,
    "usage": None,
    "session_id": None,
    "duration_ms": None,
    "cost_usd": None,
    "error_class": None,
    "reset": None,
    "message": None,
}


class ParseResultAnswerTest(unittest.TestCase):
    def test_should_write_back_a_result_carrying_every_field(self):
        # Act
        document = ParseResultAnswer.from_document(RESULT_OF_A_RATE_LIMITED_RUN).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "outcome": "failed",
                "steps": 31,
                "usage": {
                    "input_tokens": 1200,
                    "output_tokens": 340,
                    "cache_creation_input_tokens": 50,
                    "cache_read_input_tokens": 9000,
                },
                "session_id": "session-b74",
                "duration_ms": 61000,
                "cost_usd": 1.27,
                "error_class": "rate_limit",
                "reset": {"hour": "3pm", "timezone": "Europe/Paris"},
                "message": "usage limit reached",
            },
        )

    def test_should_write_back_a_result_whose_nullable_fields_are_null(self):
        # Act
        document = ParseResultAnswer.from_document(RESULT_REPORTING_NOTHING).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "outcome": "done",
                "steps": None,
                "usage": None,
                "session_id": None,
                "duration_ms": None,
                "cost_usd": None,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )

    def test_should_write_back_a_reset_hour_given_with_no_time_zone(self):
        # Arrange
        document = {**RESULT_OF_A_RATE_LIMITED_RUN, "reset": {"hour": "15:00", "timezone": None}}

        # Act
        reset = ParseResultAnswer.from_document(document).to_document()["reset"]

        # Assert
        self.assertEqual(reset, {"hour": "15:00", "timezone": None})
