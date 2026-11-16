import argparse
import contextlib
import functools
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.preflight import COMMAND, preflight
from brigade.errors import BrigadeError
from brigade.system.resolve_plugin import resolve_plugin
from tests.unit.commands.command_runtime import create_machine_double, write_ledger
from tests.unit.create_preflight_plugins import resolve_preflight_kinds_or
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

NO_PLUGIN_SOURCES = None
PARAMETERS = ["pr=42", "task=B1", "base=integration/w1"]
VERIFY_PULL_REQUEST = "verify-pull-request"
TASK_WORKTREE = {
    ("git", "rev-parse", "--show-toplevel"): "/srv/tidepool-T7\n",
    ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): "/srv/tidepool/.git\n",
}
TIDEPOOL_PROJECT = (("PATH", "/srv/tidepool"),)
GITHUB_PROJECT = (*TIDEPOOL_PROJECT, ("FORGE", "github"))
TIDEPOOL_TASKS = {"T7": (("MILESTONE", "@MILESTONE.M4"),)}
M4_BRANCH_CUT = {
    "schema_version": 1,
    "ts": "2026-09-29T22:00:00Z",
    "event": "milestone.branch_cut",
    "project": "tidepool",
    "milestone": "M4",
    "branch": "integration/M4-tides",
    "login": None,
}
WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-09-30T22:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "tasks": ["T7"],
}
TASK_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-01T22:00:00Z",
    "event": "task.pr_opened",
    "project": "tidepool",
    "task": "T7",
    "wave": "tidepool_w16",
    "branch": "task/M4-tides/T7",
    "pr": 42,
    "login": "tidepool-bot",
}
PASSED_CHECK = {"result": "ok", "name": "ci", "findings": []}
FAILED_CHECK = {"result": "fail", "name": "scope", "findings": ["brigade/cli.py is outside the task"]}


class ForgeDeclineDouble:
    def __init__(self):
        self.questions = []

    def __getattr__(self, operation: str):
        def decline(request: dict, runtime) -> dict:
            self.questions.append((operation, request))
            raise BrigadeError(f"the forge double declines {operation}")

        return decline


class ForgeBindingItsLoginsDouble(ForgeDeclineDouble):
    def read_login_environment(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "environment": {"GH_TOKEN": f"token-of-{request['login']}"}}

    def describe_account(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "login": request["environment"]["GH_TOKEN"].removeprefix("token-of-")}


SHOP_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-19T08:00:00Z",
    "event": "task.pr_opened",
    "project": "shop",
    "task": "B1",
    "wave": "shop_w1",
    "branch": "feature/B1-cart",
    "pr": 42,
    "login": "shop-bot",
}
NOT_DEFINED = ProcessAnswer(exit_code=1, stderr="awawa show: the preflight is not defined in the workspace\n")


def place_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)


class PreflightCommandTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        project = root / "shop"
        self.project = project
        worktree = project / ".brigade" / "worktrees" / "B1"
        worktree.mkdir(parents=True)
        self.enterContext(contextlib.chdir(worktree))
        head_tree = root / "cache" / "head"
        base_tree = root / "cache" / "base"
        head_tree.mkdir(parents=True)
        base_tree.mkdir(parents=True)
        collector = project / ".brigade" / "collectors" / "pull-request"
        place_executable(collector)
        pull_request = {
            "schema_version": 1,
            "collector": "pull-request",
            "collected_at": "2026-10-19T09:00:00Z",
            "cache": False,
            "summary": {
                "project": "shop",
                "pr": 42,
                "task": "B1",
                "base_branch": "integration/w1",
                "repository": str(project),
                "base_head": "1111111",
                "base": "0000000",
                "head": "2222222",
                "head_tree": str(head_tree),
                "base_tree": str(base_tree),
                "checkout": str(project),
                "folder": ".",
                "changed": [],
                "added_lines": [],
                "check_runs": [{"name": "unit", "verdict": "success"}],
                "body": "Delivers @TASK.B1.\n",
                "acceptance": [],
                "privacy": {"private": [], "public": []},
            },
            "items": [],
        }
        task = {
            "fields": [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {"name": "DELIVERED_BY", "atoms": ['"42"'], "fields": []},
            ]
        }
        paths = create_test_paths(root)
        paths.config_root.mkdir(parents=True)
        paths.schema_file.write_text("SCHEMA PROJECT\n")
        (paths.config_root / "config.toml").write_text("", encoding="utf-8")
        write_ledger(root, [SHOP_PR_OPENED])
        self.answers = {
            **create_registry_answers(
                paths.config_root, {"shop": {"PATH": str(project), "FORGE": "github", "MAIN": "integration/w1"}}
            ),
            ("awawa", "show", "@TASK.B1", "--json", str(worktree)): ProcessAnswer(stdout=json.dumps({"fields": []})),
            ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout=f"{worktree}\n"),
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                stdout=f"{project / '.git'}\n"
            ),
            (str(collector),): ProcessAnswer(stdout=json.dumps(pull_request)),
            ("awawa", "show", "@TASK.B1", "--json", str(head_tree)): ProcessAnswer(stdout=json.dumps(task)),
            ("awawa", "show", "@PREFLIGHT.verify_pull_request", "--json", str(project)): NOT_DEFINED,
            ("awawa", "show", "@PREFLIGHT.nightly", "--json", str(project)): NOT_DEFINED,
            ("awawa", "diff", str(base_tree), str(head_tree), "--json"): ProcessAnswer(
                stdout=json.dumps({"added": [], "changed": [], "removed": []})
            ),
        }
        runner = RecordingProcessRunner(self.answers)
        self.runtime = create_test_runtime(
            paths, run_process=runner, resolve_plugin=functools.partial(resolve_plugin, sources=NO_PLUGIN_SOURCES)
        )

    def test_should_print_the_document_of_the_preflight_of_the_pull_request_of_a_task(self):
        # Arrange
        request = argparse.Namespace(name=VERIFY_PULL_REQUEST, extra_arguments=["pr=42"])

        # Act
        document = preflight(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "preflight": "verify-pull-request",
                "result": "ok",
                "project": "shop",
                "pr": 42,
                "task": "B1",
                "head": "2222222",
                "checks": [
                    {"name": "ancestry", "result": "ok", "findings": []},
                    {"name": "checks", "result": "ok", "findings": []},
                    {
                        "name": "corpus",
                        "result": "ok",
                        "findings": [],
                        "commands": [
                            {"command": "awawa fmt --check .", "exit_code": 0, "duration_ms": 0, "output": ""},
                            {"command": "awawa lint --strict .", "exit_code": 0, "duration_ms": 0, "output": ""},
                        ],
                    },
                    {"name": "promotion", "result": "ok", "findings": []},
                    {"name": "untouched_files", "result": "ok", "findings": []},
                    {"name": "privacy", "result": "ok", "findings": []},
                    {"name": "body", "result": "ok", "findings": []},
                    {"name": "size", "result": "info", "findings": ["0 files", "0 lines", "0 packages", "0 layers"]},
                ],
            },
        )

    def test_should_run_the_checks_of_a_custom_preflight_of_the_project(self):
        # Arrange
        nightly = {
            "file": str(self.project / "preflights.awawa"),
            "fields": [
                {"name": "TITLE", "atoms": ['"the nightly checks of the shop"'], "fields": []},
                {"name": "COLLECTOR", "atoms": ['"pull-request"'], "fields": []},
                {"name": "CHECK", "atoms": ['"body"'], "fields": []},
            ],
        }
        self.answers[("awawa", "show", "@PREFLIGHT.nightly", "--json", str(self.project))] = ProcessAnswer(
            stdout=json.dumps(nightly)
        )
        request = argparse.Namespace(name="nightly", extra_arguments=PARAMETERS)

        # Act
        document = preflight(request, self.runtime)

        # Assert
        self.assertEqual(document["checks"], [{"name": "body", "result": "ok", "findings": []}])
        self.assertEqual(document["result"], "ok")

    def test_should_refuse_a_name_no_preflight_carries(self):
        # Arrange
        request = argparse.Namespace(name="nightly", extra_arguments=PARAMETERS)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            preflight(request, self.runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "no preflight nightly in the project, in the machine's preflights directory or among the built-ins",
        )


class PreflightCommandRenderingTest(unittest.TestCase):
    def test_should_print_the_verdict_and_the_findings_of_each_check(self):
        # Arrange
        document = {
            "schema_version": 1,
            "preflight": "verify-pull-request",
            "parameters": {"pr": "42"},
            "result": "fail",
            "checks": [
                {"name": "privacy", "result": "fail", "findings": ["cart.py:1: a home path"]},
                {"name": "body", "result": "ok", "findings": []},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "preflight verify-pull-request\nfail  privacy\n  cart.py:1: a home path\nok  body")

    def test_should_exit_1_on_a_preflight_that_fails_and_0_on_one_that_passes(self):
        # Arrange
        rows = [("fail", 1), ("ok", 0)]
        for result, expected_exit_code in rows:
            with self.subTest(result=result):
                # Act
                exit_code = COMMAND.decide_exit_code({"result": result})

                # Assert
                self.assertEqual(exit_code, expected_exit_code)

    def test_should_take_a_key_value_pair_as_a_parameter_and_an_option_as_none(self):
        # Arrange
        rows = [("pr=42", True), ("--json", False), ("--format=json", False), ("verify-pull-request", False)]
        for argument, expected in rows:
            with self.subTest(argument=argument):
                # Act
                accepted = COMMAND.accept_extra_argument(argument)

                # Assert
                self.assertEqual(accepted, expected)


class PreflightOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [M4_BRANCH_CUT, WAVE_STARTED, TASK_PR_OPENED])
        self.forge = ForgeDeclineDouble()
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(
                {"PROJECT": {"tidepool": GITHUB_PROJECT}, "TASK": TIDEPOOL_TASKS}, TASK_WORKTREE
            ),
            resolve_plugin=resolve_preflight_kinds_or(lambda kind, name, **places: self.forge),
        )

    def test_should_ask_the_forge_about_the_pull_request_of_the_task(self):
        # Act
        with self.assertRaises(BrigadeError):
            preflight(Namespace(name=VERIFY_PULL_REQUEST, extra_arguments=["pr=42"]), self.runtime)

        # Assert
        self.assertEqual(
            self.forge.questions,
            [
                (
                    "read_pull_request",
                    {"schema_version": 1, "repository": "/srv/tidepool", "number": 42, "environment": {}},
                )
            ],
        )

    def test_should_refuse_a_pull_request_no_task_opened(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            preflight(Namespace(name=VERIFY_PULL_REQUEST, extra_arguments=["pr=41"]), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no task.pr_opened of @PROJECT.tidepool names the pull request #41")


class PreflightOfAPullRequestAsTheLoginOfTheCliKeyTest(unittest.TestCase):
    def test_should_read_the_pull_request_as_the_login_of_the_cli_key(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text(
            '[forge_accounts]\ncli = "octo-cli"\nbuild = "octo-bot"\n', encoding="utf-8"
        )
        write_ledger(root, [M4_BRANCH_CUT, WAVE_STARTED, TASK_PR_OPENED])
        forge = ForgeBindingItsLoginsDouble()
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_machine_double(
                {"PROJECT": {"tidepool": GITHUB_PROJECT}, "TASK": TIDEPOOL_TASKS}, TASK_WORKTREE
            ),
            resolve_plugin=resolve_preflight_kinds_or(lambda kind, name, **places: forge),
        )

        # Act
        with self.assertRaises(BrigadeError):
            preflight(Namespace(name=VERIFY_PULL_REQUEST, extra_arguments=["pr=42"]), runtime)

        # Assert
        self.assertEqual(
            forge.questions,
            [
                (
                    "read_pull_request",
                    {
                        "schema_version": 1,
                        "repository": "/srv/tidepool",
                        "number": 42,
                        "environment": {"GH_TOKEN": "token-of-octo-cli"},
                    },
                )
            ],
        )

    def test_should_read_no_login_environment_on_a_project_of_forge_none(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text('[forge_accounts]\ncli = "octo-cli"\n', encoding="utf-8")
        write_ledger(root, [M4_BRANCH_CUT, WAVE_STARTED, TASK_PR_OPENED])
        forge = ForgeBindingItsLoginsDouble()
        local_project = (*TIDEPOOL_PROJECT, ("FORGE", "none"))
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_machine_double(
                {"PROJECT": {"tidepool": local_project}, "TASK": TIDEPOOL_TASKS}, TASK_WORKTREE
            ),
            resolve_plugin=resolve_preflight_kinds_or(lambda kind, name, **places: forge),
        )

        # Act
        with self.assertRaises(BrigadeError):
            preflight(Namespace(name=VERIFY_PULL_REQUEST, extra_arguments=["pr=42"]), runtime)

        # Assert
        self.assertEqual(
            forge.questions,
            [
                (
                    "read_pull_request",
                    {"schema_version": 1, "repository": "/srv/tidepool", "number": 42, "environment": {}},
                )
            ],
        )
