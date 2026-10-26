import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

FIRST_DAY = "2026-09-20T09:00:00Z"
ECHO_COLLECTOR = (
    "#!/bin/sh\n"
    'echo ran >> "$BRIGADE_PROJECT_PATH/.brigade/echo-runs"\n'
    'printf \'{"schema_version": 1, "collector": "echo", "collected_at": "2026-10-15T08:00:00Z", "cache": true,'
    ' "summary": {"project": "%s", "since": "%s", "parameters": %s}, "items": []}\\n\''
    ' "$BRIGADE_PROJECT_PATH" "$BRIGADE_SINCE" "$BRIGADE_PARAMS"\n'
)
MACHINE_COLLECTOR = (
    "#!/bin/sh\n"
    'echo \'{"schema_version": 1, "collector": "echo", "collected_at": "2026-10-15T08:00:00Z",'
    ' "summary": {"origin": "machine"}, "items": []}\'\n'
)
PATH_COLLECTOR = (
    "#!/bin/sh\n"
    'echo \'{"schema_version": 1, "collector": "any", "collected_at": "2026-10-15T08:00:00Z",'
    ' "summary": {"origin": "PATH"}, "items": []}\'\n'
)
FAILING_COLLECTOR = (
    "#!/bin/sh\n"
    'echo ran >> "$BRIGADE_PROJECT_PATH/.brigade/failing-runs"\n'
    'for line in $(seq 1 25); do echo "line $line" >&2; done\n'
    "exit 3\n"
)
LAST_TWENTY_LINES = (
    "line 6\nline 7\nline 8\nline 9\nline 10\nline 11\nline 12\nline 13\nline 14\nline 15\n"
    "line 16\nline 17\nline 18\nline 19\nline 20\nline 21\nline 22\nline 23\nline 24\nline 25\n"
)


def install_executable(path: Path, script: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script)
    path.chmod(0o755)


class CollectTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.root_path = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(self.root_path)
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.project = TemporaryProject(
            self.root_path / "projects" / "app",
            {**self.machine.describe_environment(), "GIT_AUTHOR_DATE": FIRST_DAY, "GIT_COMMITTER_DATE": FIRST_DAY},
        )
        self.project.write("README.md", "app\n")
        self.project.track("README.md")
        self.project.run_git("commit", "--quiet", "-m", "start the app")
        self.project_collectors = self.project.path / ".brigade" / "collectors"
        self.machine_collectors = self.machine.config_home / "brigade" / "collectors"
        self.path_collectors = self.root_path / "bin"

    def tearDown(self):
        self.root.cleanup()

    def describe_environment_with(self, **variables: str) -> dict:
        return {**self.machine.describe_environment(), **variables}

    def describe_environment_with_collectors_on_path(self) -> dict:
        return self.describe_environment_with(PATH=f"{self.path_collectors}{os.pathsep}{self.machine.search_path}")

    def run_brigade(self, *arguments: str, environment: dict | None = None):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, *arguments, environment=environment, cwd=self.project.path)

    def run_collect(self, *arguments: str, environment: dict | None = None):
        return self.run_brigade("collect", *arguments, environment=environment)


class BrigadeCollectOfAProjectCollectorTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        install_executable(self.project_collectors / "echo", ECHO_COLLECTOR)

    def test_should_hand_the_collector_the_project_the_since_and_the_parameters(self):
        # Act
        completed = self.run_collect("echo", "window=week", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "collector": "echo",
                "source": "project",
                "cached": False,
                "summary": {"project": str(self.project.path), "since": "2026-10-01", "parameters": {"window": "week"}},
                "document": mock.ANY,
            },
        )


class BrigadeCollectInsideARunTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        install_executable(self.project_collectors / "echo", ECHO_COLLECTOR)
        self.run_directory = self.root_path / "runs" / "20261015T080000Z-a00001"
        self.run_directory.mkdir(parents=True)

    def test_should_print_the_summary_and_the_document_of_the_run(self):
        # Act
        completed = self.run_collect(
            "echo",
            "window=week",
            "--since",
            "2026-10-01",
            environment=self.describe_environment_with(BRIGADE_RUN_DIR=str(self.run_directory)),
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "echo collected",
                f"project     {self.project.path}",
                "since       2026-10-01",
                'parameters  {"window": "week"}',
                f"document    {self.run_directory / 'collect' / 'echo' / 'document.json'}",
            ],
        )


class BrigadeCollectOfAFailingCollectorTest(CollectTestCase):
    def test_should_name_the_collector_its_exit_code_and_the_last_twenty_lines_of_its_stderr(self):
        # Arrange
        install_executable(self.project_collectors / "failing", FAILING_COLLECTOR)

        # Act
        completed = self.run_collect("failing")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, f"brigade collect: collector failing exited 3\n{LAST_TWENTY_LINES}")


class BrigadeCollectorsListTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        install_executable(self.project_collectors / "alpha", ECHO_COLLECTOR)
        install_executable(self.machine_collectors / "beta", MACHINE_COLLECTOR)
        install_executable(self.path_collectors / "brigade-collector-gamma", PATH_COLLECTOR)

    def test_should_list_the_collectors_of_the_four_sources(self):
        # Act
        completed = self.run_brigade(
            "collectors", "list", "--json", environment=self.describe_environment_with_collectors_on_path()
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "collectors": [
                    {"name": "alpha", "source": "project", "absent": None},
                    {"name": "beta", "source": "machine", "absent": None},
                    {"name": "gamma", "source": "PATH", "absent": None},
                    {"name": "check-runs", "source": "built-in", "absent": None},
                    {"name": "corpus", "source": "built-in", "absent": None},
                    {"name": "git-diff-stat", "source": "built-in", "absent": None},
                    {"name": "git-log", "source": "built-in", "absent": None},
                    {"name": "inbox-families", "source": "built-in", "absent": None},
                    {"name": "ledger", "source": "built-in", "absent": None},
                    {"name": "pr-list", "source": "built-in", "absent": None},
                    {"name": "pr-threads", "source": "built-in", "absent": None},
                    {"name": "shell", "source": "built-in", "absent": None},
                    {"name": "study", "source": "built-in", "absent": None},
                    {"name": "worktrees", "source": "built-in", "absent": None},
                ],
            },
        )

    def test_should_list_the_collectors_as_text(self):
        # Act
        completed = self.run_brigade(
            "collectors", "list", environment=self.describe_environment_with_collectors_on_path()
        )

        # Assert
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "name            source    absent",
                "alpha           project   -",
                "beta            machine   -",
                "gamma           PATH      -",
                "check-runs      built-in  -",
                "corpus          built-in  -",
                "git-diff-stat   built-in  -",
                "git-log         built-in  -",
                "inbox-families  built-in  -",
                "ledger          built-in  -",
                "pr-list         built-in  -",
                "pr-threads      built-in  -",
                "shell           built-in  -",
                "study           built-in  -",
                "worktrees       built-in  -",
            ],
        )
