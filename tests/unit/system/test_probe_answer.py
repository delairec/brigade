import unittest

from brigade.system.probe_answer import ProbeAnswer

PROBE_OF_A_CLIENT_EXECUTABLE = {
    "schema_version": 1,
    "client": "claude-code",
    "version_argv": ["claude", "--version"],
    "operations": ["probe", "launch", "result"],
    "features": ["step_count", "tool_grants"],
    "models": {"standard": "opus"},
}
PROBE_OF_NO_CLIENT_EXECUTABLE = {
    "schema_version": 1,
    "client": "fake",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {},
}


class ProbeAnswerTest(unittest.TestCase):
    def test_should_write_back_the_answer_of_a_client_with_an_executable(self):
        # Act
        document = ProbeAnswer.from_document(PROBE_OF_A_CLIENT_EXECUTABLE).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "client": "claude-code",
                "version_argv": ["claude", "--version"],
                "operations": ["probe", "launch", "result"],
                "features": ["step_count", "tool_grants"],
                "models": {"standard": "opus"},
            },
        )

    def test_should_write_back_the_answer_of_a_client_with_no_executable(self):
        # Act
        document = ProbeAnswer.from_document(PROBE_OF_NO_CLIENT_EXECUTABLE).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "client": "fake",
                "version_argv": None,
                "operations": ["probe"],
                "features": [],
                "models": {},
            },
        )
