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

PROBE_OF_A_CLIENT_ANSWERING_AN_ATTRIBUTION = {
    "schema_version": 1,
    "client": "fake",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {},
    "attribution": ["Co-Authored-By: Fake Model <fake@example.org>"],
}
PROBE_OF_A_CLIENT_NAMING_ITS_EDIT_TOOLS = {
    "schema_version": 1,
    "client": "claude-code",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {},
    "edit_tools": ["Edit", "Write", "NotebookEdit"],
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

    def test_should_write_back_the_attribution_lines_the_client_answers(self):
        # Act
        document = ProbeAnswer.from_document(PROBE_OF_A_CLIENT_ANSWERING_AN_ATTRIBUTION).to_document()

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
                "attribution": ["Co-Authored-By: Fake Model <fake@example.org>"],
            },
        )

    def test_should_write_back_the_edit_tools_the_client_names(self):
        # Act
        document = ProbeAnswer.from_document(PROBE_OF_A_CLIENT_NAMING_ITS_EDIT_TOOLS).to_document()

        # Assert
        self.assertEqual(document["edit_tools"], ["Edit", "Write", "NotebookEdit"])
