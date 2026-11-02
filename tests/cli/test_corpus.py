import http.client
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject
from tests.process_launcher import ProcessLauncher

RELAY_EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables" / "awawa-relay"
FETCH_WAIT_S = 60.0


class CorpusTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.project = TemporaryProject(root / "projects" / "app", self.machine.describe_environment())
        self.project.write("corpus/tasks.awawa", 'TASK B1\n\tTITLE "committed"\n')
        self.project.track("corpus/tasks.awawa")
        self.project.run_git("commit", "--quiet", "-m", "first")
        self.sha = self.project.run_git("rev-parse", "HEAD").strip()
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.refs = self.machine.cache_home / "brigade" / "refs"

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


class BrigadeCorpusWithNoRefTest(CorpusTestCase):
    def test_should_read_the_main_branch_of_the_project_with_the_types_of_its_corpus(self):
        # Act
        completed = self.run_corpus("app", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "project": "app",
                "ref": "main",
                "sha": self.sha,
                "kind": "archive",
                "root": str(self.refs / "app" / self.sha),
                "types": ["TASK"],
            },
        )


class BrigadeServeOfTheCorpusWithNoRefTest(CorpusTestCase):
    def setUp(self):
        super().setUp()
        process = ProcessLauncher.start(
            [sys.executable, str(CLONE_ENTRY_POINT), "serve", "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(process.communicate)
        self.addCleanup(process.kill)
        self.address = urlsplit(process.stdout.readline().strip())

    def fetch(self, path: str) -> http.client.HTTPResponse:
        connection = http.client.HTTPConnection(self.address.hostname, self.address.port, timeout=FETCH_WAIT_S)
        self.addCleanup(connection.close)
        connection.request("GET", path)
        return connection.getresponse()

    def test_should_open_the_view_with_the_main_branch_and_the_types_of_the_corpus(self):
        # Act
        response = self.fetch("/views/corpus/app")

        # Assert
        body = response.read().decode()
        self.assertEqual(response.status, 200, body)
        self.assertIn('<input name="ref" value="main">', body)
        self.assertIn('<datalist id="corpus-types"><option value="TASK"></option></datalist>', body)

    def test_should_answer_the_document_of_the_main_branch_with_its_types(self):
        # Act
        response = self.fetch("/api/corpus/app")

        # Assert
        body = response.read().decode()
        self.assertEqual(response.status, 200, body)
        self.assertEqual(
            json.loads(body),
            {
                "schema_version": 1,
                "project": "app",
                "ref": "main",
                "sha": self.sha,
                "kind": "archive",
                "root": str(self.refs / "app" / self.sha),
                "types": ["TASK"],
            },
        )


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
