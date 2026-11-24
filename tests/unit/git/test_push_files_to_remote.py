import unittest
from pathlib import Path

from brigade.git.push_files_to_remote import FilesPush, push_files_to_remote
from brigade.system.run_process import ProcessRequest
from tests.unit.recording_process_runner import RecordingProcessRunner

BOT_ENVIRONMENT = {"GH_TOKEN": "bot-token"}


class PushFilesToRemoteTest(unittest.TestCase):
    def test_should_clone_the_remote_commit_the_files_and_push_them_as_the_account(self):
        # Arrange
        git = RecordingProcessRunner()
        push = FilesPush(
            remote="https://gist.github.com/0f1e2d.git",
            clone=Path("/state/captures/shop/B1/1a2b3c4/gist.git"),
            tree=Path("/state/captures/shop/B1/1a2b3c4"),
            files=("tides-delivered.png", "tides-reference.png"),
            message="captures of @TASK.B1",
            author_name="octo-bot",
            author_email="octo-bot@users.noreply.github.com",
            credential_helper="!gh auth git-credential",
            environment=BOT_ENVIRONMENT,
        )

        # Act
        push_files_to_remote(git, push)

        # Assert
        tree = (
            "--git-dir",
            "/state/captures/shop/B1/1a2b3c4/gist.git",
            "--work-tree",
            "/state/captures/shop/B1/1a2b3c4",
        )
        self.assertEqual(
            git.requests,
            [
                ProcessRequest(
                    argv=(
                        "git",
                        "clone",
                        "--bare",
                        "https://gist.github.com/0f1e2d.git",
                        "/state/captures/shop/B1/1a2b3c4/gist.git",
                    ),
                    cwd="/state/captures/shop/B1/1a2b3c4",
                    timeout_s=120.0,
                    environment={"GH_TOKEN": "bot-token"},
                ),
                ProcessRequest(
                    argv=("git", *tree, "add", "tides-delivered.png", "tides-reference.png"),
                    cwd="/state/captures/shop/B1/1a2b3c4",
                    timeout_s=10.0,
                    environment={"GH_TOKEN": "bot-token"},
                ),
                ProcessRequest(
                    argv=(
                        "git",
                        "-c",
                        "user.name=octo-bot",
                        "-c",
                        "user.email=octo-bot@users.noreply.github.com",
                        *tree,
                        "commit",
                        "--message",
                        "captures of @TASK.B1",
                    ),
                    cwd="/state/captures/shop/B1/1a2b3c4",
                    timeout_s=30.0,
                    environment={"GH_TOKEN": "bot-token"},
                ),
                ProcessRequest(
                    argv=(
                        "git",
                        "-c",
                        "credential.helper=",
                        "-c",
                        "credential.helper=!gh auth git-credential",
                        *tree,
                        "push",
                        "origin",
                        "HEAD",
                    ),
                    cwd="/state/captures/shop/B1/1a2b3c4",
                    timeout_s=120.0,
                    environment={"GH_TOKEN": "bot-token"},
                ),
            ],
        )
