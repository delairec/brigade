import unittest

from brigade.runs.run_result import RunResult

RESULT_OF_A_FAILED_RUN = {
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
    "error_class": "rate_limit",
    "reset": {"hour": "3pm", "timezone": "Europe/Paris"},
    "message": "usage limit reached",
}
RESULT_OF_A_CUT_RUN = {
    "schema_version": 1,
    "outcome": "wall_limit",
    "steps": None,
    "usage": None,
    "session_id": None,
    "duration_ms": 1500000,
    "error_class": None,
    "reset": None,
    "message": None,
}


class RunResultTest(unittest.TestCase):
    def test_should_write_back_a_result_carrying_every_field(self):
        # Act
        document = RunResult.from_document(RESULT_OF_A_FAILED_RUN).to_document()

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
                "error_class": "rate_limit",
                "reset": {"hour": "3pm", "timezone": "Europe/Paris"},
                "message": "usage limit reached",
            },
        )

    def test_should_write_back_a_result_whose_nullable_fields_are_null(self):
        # Act
        document = RunResult.from_document(RESULT_OF_A_CUT_RUN).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "outcome": "wall_limit",
                "steps": None,
                "usage": None,
                "session_id": None,
                "duration_ms": 1500000,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )
