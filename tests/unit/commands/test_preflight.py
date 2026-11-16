import argparse
import contextlib
import functools
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.preflight import COMMAND, preflight
from brigade.errors import BrigadeError
from brigade.system.resolve_plugin import resolve_plugin
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

NO_PLUGIN_SOURCES = None
PARAMETERS = ["pr=42", "task=B1", "base=integration/w1"]
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
        self.answers = {
            **create_registry_answers(paths.config_root, {"shop": {"PATH": str(project), "FORGE": "none"}}),
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

    def test_should_run_the_checks_of_the_preflight_named_on_the_main_checkout(self):
        # Arrange
        request = argparse.Namespace(name="verify-pull-request", extra_arguments=PARAMETERS)

        # Act
        document = preflight(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "preflight": "verify-pull-request",
                "parameters": {"pr": "42", "task": "B1", "base": "integration/w1"},
                "verdict": "pass",
                "checks": [
                    {"name": "ancestry", "verdict": "pass", "findings": []},
                    {"name": "checks", "verdict": "pass", "findings": []},
                    {
                        "name": "corpus",
                        "verdict": "pass",
                        "findings": [],
                        "commands": [
                            {"command": "awawa fmt --check .", "exit_code": 0, "duration_ms": 0, "output": ""},
                            {"command": "awawa lint --strict .", "exit_code": 0, "duration_ms": 0, "output": ""},
                        ],
                    },
                    {"name": "promotion", "verdict": "pass", "findings": []},
                    {"name": "untouched_files", "verdict": "pass", "findings": []},
                    {"name": "privacy", "verdict": "pass", "findings": []},
                    {"name": "body", "verdict": "pass", "findings": []},
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
        self.assertEqual(document["checks"], [{"name": "body", "verdict": "pass", "findings": []}])
        self.assertEqual(document["verdict"], "pass")

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
            "verdict": "fail",
            "checks": [
                {"name": "privacy", "verdict": "fail", "findings": ["cart.py:1: a home path"]},
                {"name": "body", "verdict": "pass", "findings": []},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "preflight verify-pull-request\nfail  privacy\n  cart.py:1: a home path\npass  body")

    def test_should_exit_1_on_a_preflight_that_fails_and_0_on_one_that_passes(self):
        # Arrange
        rows = [("fail", 1), ("pass", 0)]
        for verdict, expected_exit_code in rows:
            with self.subTest(verdict=verdict):
                # Act
                exit_code = COMMAND.decide_exit_code({"verdict": verdict})

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
