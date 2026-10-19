import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.registry.discover_project import ProjectDiscovery, discover_project
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

ORIGIN_HEAD = ("git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
CURRENT_BRANCH = ("git", "branch", "--show-current")
ORIGIN_URL = ("git", "remote", "get-url", "origin")
CORPUS_FILES = ("git", "ls-files", "-z", "--", "*.awawa")


def create_git(corpus_files: str) -> RecordingProcessRunner:
    return RecordingProcessRunner(
        {
            ORIGIN_HEAD: ProcessAnswer(stdout="origin/main\n"),
            ORIGIN_URL: ProcessAnswer(stdout="git@github.com:ada/shop.git\n"),
            CORPUS_FILES: ProcessAnswer(stdout=corpus_files),
        }
    )


class DiscoverProjectTest(unittest.TestCase):
    def test_should_discover_the_main_branch_the_remote_and_the_corpus_directory(self):
        # Arrange
        git = create_git("corpus/tasks.awawa\0corpus/rules.awawa\0")

        # Act
        discovery = discover_project(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(
            discovery,
            ProjectDiscovery(path=Path("/srv/shop"), remote="ada/shop", main="main", corpus="corpus", forge="github"),
        )

    def test_should_place_the_corpus_at_the_root_or_nowhere(self):
        for files, expected in [("spec.awawa\0corpus/tasks.awawa\0", "."), ("", None)]:
            with self.subTest(files=files):
                # Arrange
                git = create_git(files)

                # Act
                discovery = discover_project(git, Path("/srv/shop"))

                # Assert
                self.assertEqual(discovery.corpus, expected)

    def test_should_refuse_a_repository_with_no_main_branch_to_read(self):
        # Arrange
        git = RecordingProcessRunner({ORIGIN_HEAD: ProcessAnswer(exit_code=1), CURRENT_BRANCH: ProcessAnswer()})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            discover_project(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "/srv/shop has neither an origin/HEAD nor a branch checked out; check out its main branch",
        )
