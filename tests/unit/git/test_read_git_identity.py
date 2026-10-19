import unittest

from brigade.git.read_git_identity import GitIdentity, read_git_identity
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

NAME = ("git", "config", "--get", "user.name")
EMAIL = ("git", "config", "--get", "user.email")


class ReadGitIdentityTest(unittest.TestCase):
    def test_should_answer_the_configured_name_and_email(self):
        # Arrange
        git = RecordingProcessRunner(
            {NAME: ProcessAnswer(stdout="Ada\n"), EMAIL: ProcessAnswer(stdout="ada@example.org\n")}
        )

        # Act
        identity = read_git_identity(git)

        # Assert
        self.assertEqual(identity, GitIdentity(name="Ada", email="ada@example.org"))

    def test_should_answer_none_for_a_key_absent_or_empty(self):
        # Arrange
        git = RecordingProcessRunner({NAME: ProcessAnswer(exit_code=1), EMAIL: ProcessAnswer(stdout="\n")})

        # Act
        identity = read_git_identity(git)

        # Assert
        self.assertEqual(identity, GitIdentity(name=None, email=None))
