import tempfile
import unittest
from pathlib import Path

from brigade.git.commit_files import CommitRequest, commit_files
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class CommitFilesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name) / "repository"
        self.repository.mkdir()
        run_git(self.repository, "init", "--quiet", "--initial-branch=main")
        run_git(self.repository, "config", "user.name", "Ada Lovelace")
        run_git(self.repository, "config", "user.email", "ada@example.org")
        (self.repository / ".gitignore").write_text("config.toml\n")
        (self.repository / "_schema.awawa").write_text('SCHEMA TASK\n\tDESC "a change"\n')
        (self.repository / "config.toml").write_text("")

    def tearDown(self):
        self.root.cleanup()

    def test_should_commit_the_files_named_alone_under_the_git_identity_with_the_message(self):
        # Arrange
        request = CommitRequest(
            repository=self.repository,
            files=("_schema.awawa", ".gitignore"),
            message="brigade init: the operational corpus",
        )

        # Act
        commit_files(run_process_without_trail, request)

        # Assert
        self.assertEqual(
            run_git(self.repository, "log", "--format=%an <%ae>%n%s", "--name-only"),
            "Ada Lovelace <ada@example.org>\nbrigade init: the operational corpus\n\n.gitignore\n_schema.awawa\n",
        )

    def test_should_commit_nothing_for_files_the_repository_holds_unchanged(self):
        # Arrange
        request = CommitRequest(
            repository=self.repository, files=("_schema.awawa",), message="brigade init: the operational corpus"
        )
        commit_files(run_process_without_trail, request)

        # Act
        commit_files(run_process_without_trail, request)

        # Assert
        self.assertEqual(run_git(self.repository, "rev-list", "--count", "HEAD"), "1\n")
