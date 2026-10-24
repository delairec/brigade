import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

RELAY_EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables" / "awawa-relay"


class CorpusTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.project = TemporaryProject(root / "projects" / "app", self.machine.describe_environment())
        self.project.write("corpus/tasks.awawa", "committed\n")
        self.project.track("corpus/tasks.awawa")
        self.project.run_git("commit", "--quiet", "-m", "first")
        self.sha = self.project.run_git("rev-parse", "HEAD").strip()
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.refs = self.machine.cache_home / "brigade" / "refs"

    def tearDown(self):
        self.root.cleanup()

    def run_corpus(self, *arguments: str, environment: dict | None = None):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "corpus", *arguments, environment=environment)


class BrigadeCorpusAtABranchTest(CorpusTestCase):
    def test_should_print_the_tree_as_text(self):
        # Act
        completed = self.run_corpus("app", "--ref", "main")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "@PROJECT.app",
                "ref   main",
                f"sha   {self.sha}",
                "kind  archive",
                f"root  {self.refs / 'app' / self.sha}",
            ],
        )
        self.assertEqual(completed.stderr, "")


class BrigadeCorpusWithAwawaArgumentsTest(CorpusTestCase):
    def test_should_pass_the_output_and_the_exit_code_of_awawa_through_after_the_sha(self):
        # Arrange
        environment = {
            **self.machine.describe_environment(),
            "PATH": f"{RELAY_EXECUTABLES}{os.pathsep}{self.machine.search_path}",
        }

        # Act
        completed = self.run_corpus("app", "--ref", "main", "--", "lint", "--strict", ".", environment=environment)

        # Assert
        self.assertEqual(completed.returncode, 3)
        self.assertEqual(completed.stdout, f"awawa lint --strict . in {self.refs / 'app' / self.sha}\n")
        self.assertEqual(completed.stderr, f"brigade corpus: @PROJECT.app at {self.sha}\nawawa diagnostic\n")
