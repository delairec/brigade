import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

FIRST_DAY = "2026-09-20T09:00:00Z"
SECOND_DAY = "2026-10-02T09:00:00Z"
ECHO_COLLECTOR = (
    "#!/bin/sh\n"
    'echo ran >> "$BRIGADE_PROJECT_PATH/.brigade/echo-runs"\n'
    'printf \'{"schema_version": 1, "collector": "echo", "collected_at": "2026-10-15T08:00:00Z", "cache": true,'
    ' "summary": {"project": "%s", "since": "%s", "parameters": %s}, "items": []}\\n\''
    ' "$BRIGADE_PROJECT_PATH" "$BRIGADE_SINCE" "$BRIGADE_PARAMS"\n'
)
FRESH_COLLECTOR = (
    "#!/bin/sh\n"
    'echo ran >> "$BRIGADE_PROJECT_PATH/.brigade/fresh-runs"\n'
    'echo \'{"schema_version": 1, "collector": "fresh", "collected_at": "2026-10-15T08:00:00Z",'
    ' "summary": {"origin": "project"}, "items": []}\'\n'
)
MISDECLARED_COLLECTOR = (
    "#!/bin/sh\n"
    'echo \'{"schema_version": 1, "collector": "misdeclared", "collected_at": "2026-10-15T08:00:00Z",'
    ' "cache": "yes", "summary": {}, "items": []}\'\n'
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
SHAPELESS_COLLECTOR = (
    "#!/bin/sh\n"
    'echo \'{"schema_version": 1, "collector": "shapeless", "collected_at": "2026-10-15T08:00:00Z", "items": []}\'\n'
)
MUTE_COLLECTOR = "#!/bin/sh\necho done\n"
LAST_TWENTY_LINES = (
    "line 6\nline 7\nline 8\nline 9\nline 10\nline 11\nline 12\nline 13\nline 14\nline 15\n"
    "line 16\nline 17\nline 18\nline 19\nline 20\nline 21\nline 22\nline 23\nline 24\nline 25\n"
)
SCHEMA = (
    'SCHEMA TASK\n\tDESC "a task"\n\tFIELD TITLE string\n\t\tREQUIRED\n\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n'
)
TASKS = 'TASK T1\n\tTITLE "write the app"\n\tSTATUS todo\n'
LEDGER_LINES = (
    '{"schema_version": 1, "ts": "2026-09-30T22:00:00Z", "event": "wave.started", "wave": "app/1", "project": "app"}\n'
    '{"schema_version": 2, "ts": "2026-10-02T10:00:00Z", "event": "run.finished", "wave": "app/1", "task": "B1",'
    ' "run": "20261002T100000Z-a00001", "client": "claude-code", "project": "app", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 40, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-03T10:00:00Z", "event": "run.finished", "wave": "web/1", "task": "W1",'
    ' "run": "20261003T100000Z-a00002", "client": "claude-code", "project": "web", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 1, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "failed",'
    ' "error_class": "rate_limit", "main_steps": 50, "total_steps": null}\n'
    '{"schema_version": 1, "ts": "2026-10-04T10:00:00Z", "event": "custom.signal"}\n'
)
LATER_LEDGER_LINE = '{"schema_version": 1, "ts": "2026-10-05T10:00:00Z", "event": "custom.signal"}\n'
NOT_A_TOOL = re.compile(r"^brigade collect: ran (?!git |awawa )", re.MULTILINE)


def install_executable(path: Path, script: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script)
    path.chmod(0o755)


class CollectTestCase(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        self.root_path = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(self.root_path)
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
        self.cache = self.machine.cache_home / "brigade" / "collectors"
        self.ledger = self.machine.state_home / "brigade" / "ledger" / "2026-10.jsonl"

    def tearDown(self):
        self.root.cleanup()

    def describe_environment_with(self, **variables: str) -> dict:
        return {**self.machine.describe_environment(), **variables}

    def describe_environment_with_collectors_on_path(self) -> dict:
        return self.describe_environment_with(PATH=f"{self.path_collectors}{os.pathsep}{os.environ['PATH']}")

    def run_brigade(self, *arguments: str, environment: dict | None = None):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, *arguments, environment=environment, cwd=self.project.path)

    def run_collect(self, *arguments: str, environment: dict | None = None):
        return self.run_brigade("collect", *arguments, environment=environment)

    def register_project(self) -> None:
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))

    def commit_on(self, day: str, message: str) -> None:
        self.project.environment["GIT_AUTHOR_DATE"] = day
        self.project.environment["GIT_COMMITTER_DATE"] = day
        self.project.run_git("commit", "--quiet", "-m", message)

    def read_document(self, completed) -> dict:
        return json.loads(Path(json.loads(completed.stdout)["document"]).read_text())


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

    def test_should_write_the_document_and_its_sidecar_as_the_cache_entry(self):
        # Act
        completed = self.run_collect("echo", "window=week", "--since", "2026-10-01", "--json")

        # Assert
        document = Path(json.loads(completed.stdout)["document"])
        sidecar = json.loads(document.with_name("sidecar.json").read_text())
        self.assertEqual(
            sidecar,
            {
                "schema_version": 1,
                "collector": "echo",
                "command": str(self.project_collectors / "echo"),
                "parameters": {"window": "week"},
                "since": "2026-10-01",
                "duration_ms": mock.ANY,
                "exit_code": 0,
                "cache_key": mock.ANY,
            },
        )
        self.assertEqual(document, self.cache / "echo" / sidecar["cache_key"] / "document.json")
        self.assertEqual(
            json.loads(document.read_text()),
            {
                "schema_version": 1,
                "collector": "echo",
                "collected_at": "2026-10-15T08:00:00Z",
                "cache": True,
                "summary": {"project": str(self.project.path), "since": "2026-10-01", "parameters": {"window": "week"}},
                "items": [],
            },
        )

    def test_should_collect_since_the_beginning_without_since(self):
        # Act
        completed = self.run_collect("echo", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["summary"]["since"], "1970-01-01")


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

    def test_should_write_the_sidecar_under_the_run_directory(self):
        # Act
        self.run_collect(
            "echo",
            "--since",
            "2026-10-01",
            environment=self.describe_environment_with(BRIGADE_RUN_DIR=str(self.run_directory)),
        )

        # Assert
        self.assertEqual(
            json.loads((self.run_directory / "collect" / "echo" / "sidecar.json").read_text()),
            {
                "schema_version": 1,
                "collector": "echo",
                "command": str(self.project_collectors / "echo"),
                "parameters": {},
                "since": "2026-10-01",
                "duration_ms": mock.ANY,
                "exit_code": 0,
                "cache_key": mock.ANY,
            },
        )


class BrigadeCollectFromTheCacheTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        install_executable(self.project_collectors / "echo", ECHO_COLLECTOR)
        self.run_collect("echo", "--since", "2026-10-01")

    def test_should_answer_a_second_call_from_the_cache(self):
        # Act
        completed = self.run_collect("echo", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["cached"], True)
        self.assertEqual((self.project.path / ".brigade" / "echo-runs").read_text(), "ran\n")

    def test_should_say_the_answer_comes_from_the_cache(self):
        # Act
        completed = self.run_collect("echo", "--since", "2026-10-01")

        # Assert
        self.assertEqual(completed.stdout.splitlines()[0], "echo from cache")

    def test_should_collect_again_with_refresh(self):
        # Act
        completed = self.run_collect("echo", "--since", "2026-10-01", "--refresh", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["cached"], False)
        self.assertEqual((self.project.path / ".brigade" / "echo-runs").read_text(), "ran\nran\n")

    def test_should_collect_again_for_another_since(self):
        # Act
        completed = self.run_collect("echo", "--since", "0d", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["cached"], False)


class BrigadeCollectOfACollectorDeclaringNoCacheTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        install_executable(self.project_collectors / "fresh", FRESH_COLLECTOR)
        self.run_directory = self.root_path / "runs" / "20261015T080000Z-a00001"
        self.run_directory.mkdir(parents=True)

    def test_should_collect_afresh_on_every_call(self):
        # Arrange
        self.run_collect("fresh")

        # Act
        completed = self.run_collect("fresh", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["cached"], False)
        self.assertEqual((self.project.path / ".brigade" / "fresh-runs").read_text(), "ran\nran\n")

    def test_should_collect_afresh_on_every_call_inside_a_run(self):
        # Arrange
        inside_the_run = self.describe_environment_with(BRIGADE_RUN_DIR=str(self.run_directory))
        self.run_collect("fresh", environment=inside_the_run)

        # Act
        completed = self.run_collect("fresh", "--json", environment=inside_the_run)

        # Assert
        self.assertEqual(json.loads(completed.stdout)["cached"], False)
        self.assertEqual((self.project.path / ".brigade" / "fresh-runs").read_text(), "ran\nran\n")

    def test_should_leave_nothing_in_the_cache(self):
        # Act
        self.run_collect("fresh")

        # Assert
        self.assertEqual(self.cache.exists(), False)

    def test_should_write_the_document_under_the_state_directory_outside_a_run(self):
        # Act
        completed = self.run_collect("fresh", "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["document"],
            str(self.machine.state_home / "brigade" / "collect" / "fresh" / "document.json"),
        )

    def test_should_write_the_document_under_the_run_directory_inside_a_run(self):
        # Act
        completed = self.run_collect(
            "fresh", "--json", environment=self.describe_environment_with(BRIGADE_RUN_DIR=str(self.run_directory))
        )

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["document"], str(self.run_directory / "collect" / "fresh" / "document.json")
        )

    def test_should_refuse_a_cache_declaration_that_is_no_boolean(self):
        # Arrange
        install_executable(self.project_collectors / "misdeclared", MISDECLARED_COLLECTOR)

        # Act
        completed = self.run_collect("misdeclared")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade collect: collector misdeclared exited 0: its document cache is a string, not a boolean\n",
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

    def test_should_never_cache_a_failure(self):
        # Arrange
        install_executable(self.project_collectors / "failing", FAILING_COLLECTOR)
        self.run_collect("failing")

        # Act
        self.run_collect("failing")

        # Assert
        self.assertEqual((self.project.path / ".brigade" / "failing-runs").read_text(), "ran\nran\n")

    def test_should_name_the_key_a_document_lacks(self):
        # Arrange
        install_executable(self.project_collectors / "shapeless", SHAPELESS_COLLECTOR)

        # Act
        completed = self.run_collect("shapeless")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade collect: collector shapeless exited 0: its document lacks the key summary\n"
        )

    def test_should_refuse_an_output_that_is_no_json_document(self):
        # Arrange
        install_executable(self.project_collectors / "mute", MUTE_COLLECTOR)

        # Act
        completed = self.run_collect("mute")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade collect: collector mute exited 0: it printed no JSON document\n")


class BrigadeCollectResolutionTest(CollectTestCase):
    def test_should_prefer_the_project_collector_to_the_machine_one(self):
        # Arrange
        install_executable(self.project_collectors / "echo", ECHO_COLLECTOR)
        install_executable(self.machine_collectors / "echo", MACHINE_COLLECTOR)

        # Act
        completed = self.run_collect("echo", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["source"], "project")

    def test_should_prefer_the_machine_collector_to_the_one_on_path(self):
        # Arrange
        install_executable(self.machine_collectors / "echo", MACHINE_COLLECTOR)
        install_executable(self.path_collectors / "brigade-collector-echo", PATH_COLLECTOR)

        # Act
        completed = self.run_collect("echo", "--json", environment=self.describe_environment_with_collectors_on_path())

        # Assert
        self.assertEqual(json.loads(completed.stdout)["source"], "machine")

    def test_should_prefer_the_collector_on_path_to_the_built_in(self):
        # Arrange
        install_executable(self.path_collectors / "brigade-collector-git-log", PATH_COLLECTOR)

        # Act
        completed = self.run_collect(
            "git-log", "--json", environment=self.describe_environment_with_collectors_on_path()
        )

        # Assert
        self.assertEqual(json.loads(completed.stdout)["source"], "PATH")

    def test_should_name_the_four_sources_of_an_unknown_collector(self):
        # Act
        completed = self.run_collect("nowhere")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade collect: no collector nowhere in {self.project_collectors}, in {self.machine_collectors},"
            " as brigade-collector-nowhere on PATH or among the built-ins of brigade/collectors\n",
        )

    def test_should_refuse_a_name_that_leaves_the_collector_directories(self):
        # Arrange
        install_executable(self.project.path / ".brigade" / "echo", ECHO_COLLECTOR)

        # Act
        completed = self.run_collect("../echo")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade collect: no collector ../echo in {self.project_collectors}, in {self.machine_collectors},"
            " as brigade-collector-../echo on PATH or among the built-ins of brigade/collectors\n",
        )


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
                    {"name": "alpha", "source": "project"},
                    {"name": "beta", "source": "machine"},
                    {"name": "gamma", "source": "PATH"},
                    {"name": "corpus", "source": "built-in"},
                    {"name": "git-diff-stat", "source": "built-in"},
                    {"name": "git-log", "source": "built-in"},
                    {"name": "ledger", "source": "built-in"},
                    {"name": "shell", "source": "built-in"},
                    {"name": "worktrees", "source": "built-in"},
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
                "name           source",
                "alpha          project",
                "beta           machine",
                "gamma          PATH",
                "corpus         built-in",
                "git-diff-stat  built-in",
                "git-log        built-in",
                "ledger         built-in",
                "shell          built-in",
                "worktrees      built-in",
            ],
        )


class BrigadeCollectorsListWithoutCollectorDirectoriesTest(CollectTestCase):
    def test_should_list_the_built_ins_alone(self):
        # Arrange
        missing_directory = self.root_path / "missing"

        # Act
        completed = self.run_brigade(
            "collectors", "list", "--json", environment=self.describe_environment_with(PATH=str(missing_directory))
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "collectors": [
                    {"name": "corpus", "source": "built-in"},
                    {"name": "git-diff-stat", "source": "built-in"},
                    {"name": "git-log", "source": "built-in"},
                    {"name": "ledger", "source": "built-in"},
                    {"name": "shell", "source": "built-in"},
                    {"name": "worktrees", "source": "built-in"},
                ],
            },
        )


class BrigadeCollectGitLogTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        self.project.write("README.md", "app, a shop\n")
        self.project.write("src/app.py", "")
        self.project.track("README.md", "src/app.py")
        self.commit_on(SECOND_DAY, "add the app")

    def test_should_count_the_commits_and_the_files_since_the_day(self):
        # Act
        completed = self.run_collect("git-log", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["summary"], {"commits": 1, "files": 2})

    def test_should_describe_each_commit_since_the_day(self):
        # Arrange
        sha = self.project.run_git("rev-parse", "HEAD").strip()

        # Act
        completed = self.run_collect("git-log", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(
            self.read_document(completed)["items"],
            [
                {
                    "sha": sha,
                    "author": "Ada Lovelace",
                    "date": "2026-10-02T09:00:00Z",
                    "subject": "add the app",
                    "files": ["README.md", "src/app.py"],
                }
            ],
        )

    def test_should_list_no_file_for_a_merge_commit(self):
        # Arrange
        self.project.run_git("checkout", "--quiet", "-b", "feat/shop")
        self.project.write("src/shop.py", "")
        self.project.track("src/shop.py")
        self.commit_on(SECOND_DAY, "open the shop")
        self.project.run_git("checkout", "--quiet", "main")
        self.project.run_git("merge", "--quiet", "--no-ff", "-m", "merge the shop", "feat/shop")
        sha = self.project.run_git("rev-parse", "HEAD").strip()

        # Act
        completed = self.run_collect("git-log", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(
            self.read_document(completed)["items"][0],
            {
                "sha": sha,
                "author": "Ada Lovelace",
                "date": "2026-10-02T09:00:00Z",
                "subject": "merge the shop",
                "files": [],
            },
        )

    def test_should_collect_again_once_head_moved(self):
        # Arrange
        self.run_collect("git-log", "--since", "2026-10-01")
        self.project.write("src/app.py", "print('shop')\n")
        self.project.track("src/app.py")
        self.commit_on(SECOND_DAY, "print the shop")

        # Act
        completed = self.run_collect("git-log", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["summary"], {"commits": 2, "files": 2})


class BrigadeCollectGitDiffStatTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        self.register_project()
        self.project.run_git("checkout", "--quiet", "-b", "feat/shop")
        self.project.write("README.md", "app, a shop\nopen on Sundays\n")
        self.project.track("README.md")
        self.commit_on(SECOND_DAY, "describe the shop")

    def test_should_total_the_changes_from_the_main_branch_to_head(self):
        # Act
        completed = self.run_collect("git-diff-stat", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["summary"], {"files": 1, "insertions": 2, "deletions": 1})

    def test_should_describe_each_file_between_the_refs_the_parameters_name(self):
        # Arrange
        self.project.run_git("checkout", "--quiet", "main")

        # Act
        completed = self.run_collect("git-diff-stat", "from=feat/shop", "to=main", "--json")

        # Assert
        self.assertEqual(
            self.read_document(completed)["items"], [{"path": "README.md", "insertions": 1, "deletions": 2}]
        )


class BrigadeCollectWorktreesTest(CollectTestCase):
    def test_should_describe_each_worktree_of_the_repository(self):
        # Arrange
        review = self.root_path / "review"
        side = self.root_path / "side"
        self.project.run_git("worktree", "add", "--quiet", "--detach", str(review))
        self.project.run_git("worktree", "add", "--quiet", "--lock", "-b", "side", str(side))
        sha = self.project.run_git("rev-parse", "HEAD").strip()

        # Act
        completed = self.run_collect("worktrees", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["summary"], {"worktrees": 3})
        self.assertEqual(
            self.read_document(completed)["items"],
            [
                {"path": str(self.project.path), "branch": "main", "head": sha, "detached": False, "locked": False},
                {"path": str(review), "branch": None, "head": sha, "detached": True, "locked": False},
                {"path": str(side), "branch": "side", "head": sha, "detached": False, "locked": True},
            ],
        )


class BrigadeCollectCorpusTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        self.project.write("corpus/_schema.awawa", SCHEMA)
        self.project.write("corpus/tasks.awawa", TASKS)
        self.project.track("corpus/_schema.awawa", "corpus/tasks.awawa")
        self.commit_on(SECOND_DAY, "plan the app")

    def test_should_count_the_entities_by_type_and_status(self):
        # Arrange
        self.register_project()

        # Act
        completed = self.run_collect("corpus", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["summary"], {"SCHEMA": {"todo": 0}, "TASK": {"todo": 1}})

    def test_should_describe_the_entities_at_the_ref_the_parameter_names(self):
        # Arrange
        self.register_project()
        self.project.write("corpus/tasks.awawa", f'{TASKS}\nTASK T2\n\tTITLE "sell"\n\tSTATUS todo\n')
        self.project.track("corpus/tasks.awawa")
        self.commit_on(SECOND_DAY, "plan the sale")

        # Act
        completed = self.run_collect("corpus", "ref=HEAD~1", "--json")

        # Assert
        self.assertEqual(
            self.read_document(completed)["items"],
            [
                {
                    "type": "SCHEMA",
                    "name": "TASK",
                    "target": "@SCHEMA.TASK",
                    "file": "./corpus/_schema.awawa",
                    "line": 1,
                    "status": None,
                    "incoming": 0,
                    "incoming_by": [],
                },
                {
                    "type": "TASK",
                    "name": "T1",
                    "target": "@TASK.T1",
                    "file": "./corpus/tasks.awawa",
                    "line": 1,
                    "status": "todo",
                    "incoming": 0,
                    "incoming_by": [],
                },
            ],
        )

    def test_should_fail_on_a_project_that_is_not_registered(self):
        # Act
        completed = self.run_collect("corpus")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade collect: collector corpus exited 1\nno registered project at {self.project.path}\n",
        )


class BrigadeCollectLedgerTest(CollectTestCase):
    def setUp(self):
        super().setUp()
        self.ledger.parent.mkdir(parents=True)
        self.ledger.write_text(LEDGER_LINES)

    def test_should_narrow_the_events_to_the_registered_project(self):
        # Arrange
        self.register_project()

        # Act
        completed = self.run_collect("ledger", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_document(completed)["items"],
            [{"ts": "2026-10-02T10:00:00Z", "event": "run.finished", "project": "app"}],
        )

    def test_should_aggregate_every_event_since_the_day_outside_a_registered_project(self):
        # Act
        completed = self.run_collect("ledger", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["summary"],
            {"events": {"custom.signal": 1, "run.finished": 2}, "outcomes": {"done": 1, "failed": 1}},
        )

    def test_should_collect_again_once_the_ledger_grew(self):
        # Arrange
        self.run_collect("ledger", "--since", "2026-10-01")
        with self.ledger.open("a") as ledger:
            ledger.write(LATER_LEDGER_LINE)

        # Act
        completed = self.run_collect("ledger", "--since", "2026-10-01", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["summary"]["events"], {"custom.signal": 2, "run.finished": 2})


class BrigadeCollectShellTest(CollectTestCase):
    def test_should_make_each_line_the_command_prints_an_item(self):
        # Act
        completed = self.run_collect("shell", "command=printf 'alpha\\nbeta\\n'", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_document(completed)["items"], ["alpha", "beta"])

    def test_should_count_the_lines_the_command_prints(self):
        # Act
        completed = self.run_collect("shell", "command=printf 'alpha\\nbeta\\n'", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["summary"], {"lines": 2})

    def test_should_run_the_command_in_the_project(self):
        # Act
        completed = self.run_collect("shell", "command=ls", "--json")

        # Assert
        self.assertEqual(self.read_document(completed)["items"], ["README.md"])

    def test_should_run_the_command_again_at_each_call(self):
        # Arrange
        self.run_collect("shell", "command=ls")

        # Act
        completed = self.run_collect("shell", "command=ls", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["cached"], False)

    def test_should_name_the_exit_code_and_the_stderr_of_a_failing_command(self):
        # Act
        completed = self.run_collect("shell", "command=echo broken >&2; exit 4")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade collect: collector shell exited 1\nthe command exited 4\nbroken\n",
        )

    def test_should_refuse_a_call_without_a_command(self):
        # Act
        completed = self.run_collect("shell")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade collect: collector shell exited 1\nthe shell collector takes command=<line>\n"
        )


class BuiltInCollectorsTestCase(CollectTestCase):
    def setUp(self):
        super().setUp()
        self.project.write("corpus/_schema.awawa", SCHEMA)
        self.project.write("corpus/tasks.awawa", TASKS)
        self.project.track("corpus/_schema.awawa", "corpus/tasks.awawa")
        self.commit_on(SECOND_DAY, "plan the app")
        self.register_project()
        self.ledger.parent.mkdir(parents=True)
        self.ledger.write_text(LEDGER_LINES)


class BuiltInCollectorsDeclareTheCacheTest(BuiltInCollectorsTestCase):
    def test_should_answer_a_second_call_from_the_cache(self):
        for collector in ["git-log", "git-diff-stat", "worktrees", "corpus", "ledger"]:
            with self.subTest(collector=collector):
                # Arrange
                self.run_collect(collector)

                # Act
                completed = self.run_collect(collector, "--json")

                # Assert
                self.assertEqual(json.loads(completed.stdout)["cached"], True)


class BuiltInCollectorsLaunchNoModelTest(BuiltInCollectorsTestCase):
    def setUp(self):
        super().setUp()
        self.tools = self.root_path / "tools"
        self.tools.mkdir()
        (self.tools / "git").symlink_to(shutil.which("git"))
        (self.tools / "awawa").symlink_to(shutil.which("awawa"))

    def test_should_spawn_no_process_but_git_and_awawa(self):
        for collector in ["git-log", "git-diff-stat", "worktrees", "corpus", "ledger"]:
            with self.subTest(collector=collector):
                # Act
                completed = self.run_collect(
                    collector, "--verbose", environment=self.describe_environment_with(PATH=str(self.tools))
                )

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(NOT_A_TOOL.findall(completed.stderr), [])
