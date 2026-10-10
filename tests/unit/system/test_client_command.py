import unittest

from brigade.system.client_command import ClientCommand

COMMAND_WITH_STDIN = {
    "schema_version": 1,
    "argv": ["claude", "--print"],
    "environment": {"CLAUDE_MODE": "unattended"},
    "stdin": "the brief of the run",
    "session_id": "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
}
COMMAND_WITHOUT_STDIN = {
    "schema_version": 1,
    "argv": ["fake-client"],
    "environment": {},
    "stdin": None,
    "session_id": None,
}


class ClientCommandTest(unittest.TestCase):
    def test_should_write_back_a_command_reading_its_stdin(self):
        # Act
        document = ClientCommand.from_document(COMMAND_WITH_STDIN).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "argv": ["claude", "--print"],
                "environment": {"CLAUDE_MODE": "unattended"},
                "stdin": "the brief of the run",
                "session_id": "6f1c2a9e-3b7d-4e21-9a55-0c8d4b7e2f13",
            },
        )

    def test_should_write_back_a_command_reading_no_stdin(self):
        # Act
        document = ClientCommand.from_document(COMMAND_WITHOUT_STDIN).to_document()

        # Assert
        self.assertEqual(
            document,
            {"schema_version": 1, "argv": ["fake-client"], "environment": {}, "stdin": None, "session_id": None},
        )
