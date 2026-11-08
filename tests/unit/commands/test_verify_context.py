import argparse
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.add_command_parsers import add_command_parsers
from brigade.commands.verify_context import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import (
    create_machine_double,
    write_ledger,
    write_operational_corpus,
)
from tests.unit.commands.test_verify_preflight import (
    M4_BRANCH_CUT,
    TASK_PR_OPENED,
    TASK_WORKTREE,
    TIDEPOOL_PROJECT,
    TIDEPOOL_TASKS,
    WAVE_STARTED,
    ForgeDeclineDouble,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

AWAWA_CONTEXT = {
    "command": "awawa context @TASK.T7 --with-schema .",
    "exit_code": 0,
    "stderr": "",
    "output": "TASK T7\n",
}
DIFF = {"command": "git diff 0000000 8885daa", "exit_code": 0, "stderr": "", "output": "+def tide():\n"}
RULES = [
    {
        "trigger": "python_file",
        "command": "awawa context @TRIGGER.python_file",
        "exit_code": 0,
        "stderr": "",
        "output": "RULE pure\n",
    }
]
GITHUB_PROJECT = (*TIDEPOOL_PROJECT, ("FORGE", "github"))
FAILED_CHECK = {"verdict": "fail", "name": "scope", "findings": ["brigade/cli.py is outside the task"]}


PREVIOUS_VERDICT = {
    "head": "efd5ed1",
    "verdict": "changes",
    "findings": [
        {
            "id": "1",
            "grade": "high",
            "file": "src/tides.py",
            "line": 12,
            "broken": "SPEC 2 of @TASK.T7",
            "summary": "the tide table is read twice",
            "answer": "fixed by 8885daa: the table is read once",
        },
        {
            "id": "2",
            "grade": "low",
            "file": "src/ebb.py",
            "line": 3,
            "broken": "@RULE.kiss",
            "summary": None,
            "answer": None,
        },
    ],
}
REPAIR = {"command": "git diff efd5ed1 8885daa", "exit_code": 0, "stderr": "", "output": "-read()\n+cached()\n"}


def create_document(rules: list[dict] | None, previous: dict | None = None, repair: dict | None = None) -> dict:
    return {
        "pr": 42,
        "task": "T7",
        "head": "8885daa",
        "context": [AWAWA_CONTEXT],
        "diff": DIFF,
        "previous": previous,
        "repair": repair,
        "preflight": [FAILED_CHECK],
        "rules": rules,
        "grades": ["critical", "high", "medium", "low"],
    }


class VerifyContextTextTest(unittest.TestCase):
    def test_should_print_each_section_under_its_heading(self):
        # Arrange
        document = create_document(RULES)

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "# head\n8885daa\n\n"
            "# task\n$ awawa context @TASK.T7 --with-schema .\nexit 0\nTASK T7\n\n"
            "# diff\n$ git diff 0000000 8885daa\nexit 0\n+def tide():\n\n"
            "# preflight\nfail  scope\n  brigade/cli.py is outside the task\n\n"
            "# rules\n$ awawa context @TRIGGER.python_file\nexit 0\nRULE pure\n\n"
            "# grades\ncritical\nhigh\nmedium\nlow",
        )

    def test_should_leave_the_rules_out_without_an_instructions_corpus(self):
        # Arrange
        no_instructions_corpus = None

        # Act
        text = COMMAND.render_text(create_document(no_instructions_corpus))

        # Assert
        self.assertNotIn("# rules", text)

    def test_should_print_the_previous_verdict_and_the_repair_diff_after_the_diff(self):
        # Arrange
        document = create_document(RULES, PREVIOUS_VERDICT, REPAIR)

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "# head\n8885daa\n\n"
            "# task\n$ awawa context @TASK.T7 --with-schema .\nexit 0\nTASK T7\n\n"
            "# diff\n$ git diff 0000000 8885daa\nexit 0\n+def tide():\n\n"
            "# previous verdict\nhead efd5ed1\nverdict changes\n"
            "finding 1: high src/tides.py:12, broken SPEC 2 of @TASK.T7\n"
            "  summary: the tide table is read twice\n"
            "  answer: fixed by 8885daa: the table is read once\n"
            "finding 2: low src/ebb.py:3, broken @RULE.kiss\n"
            "  summary: none\n"
            "  answer: none\n\n"
            "# repair diff\n$ git diff efd5ed1 8885daa\nexit 0\n-read()\n+cached()\n\n"
            "# preflight\nfail  scope\n  brigade/cli.py is outside the task\n\n"
            "# rules\n$ awawa context @TRIGGER.python_file\nexit 0\nRULE pure\n\n"
            "# grades\ncritical\nhigh\nmedium\nlow",
        )


class VerifyContextExitCodeTest(unittest.TestCase):
    def test_should_exit_0_whatever_the_preflight_found(self):
        # Act
        exit_code = COMMAND.decide_exit_code(create_document(RULES))

        # Assert
        self.assertEqual(exit_code, 0)


class VerifyContextRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(pr=42)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)

    def test_should_take_a_context_naming_no_pull_request(self):
        # Arrange
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (COMMAND,), argparse.ArgumentParser(add_help=False))

        # Act
        options = parser.parse_args(["verify", "context"])

        # Assert
        self.assertIsNone(options.pr)


class VerifyContextOfAPullRequestTest(unittest.TestCase):
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
            resolve_plugin=lambda kind, name, **places: self.forge,
        )

    def test_should_ask_the_forge_about_the_pull_request_of_the_task(self):
        # Act
        with self.assertRaises(BrigadeError):
            COMMAND.run(Namespace(pr=42), self.runtime)

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
            COMMAND.run(Namespace(pr=41), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no task.pr_opened of @PROJECT.tidepool names the pull request #41")

    def test_should_refuse_a_context_naming_no_pull_request_on_a_project_with_a_forge(self):
        # Arrange
        no_pull_request = None

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pr=no_pull_request), self.runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "@PROJECT.tidepool acts through the forge github: the context names its pull request",
        )


def _resolve(ref: str) -> tuple[str, ...]:
    return ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")


TASK_HEAD = "8885daa"
MAIN_HEAD = "4c1d2e0"
MERGE_BASE = "0000000"
LOCAL_PROJECT = (("PATH", "/srv/tidepool"), ("MAIN", "main"), ("FORGE", "none"))
LOCAL_TASK_WORKTREE = {
    **TASK_WORKTREE,
    ("git", "branch", "--show-current"): "feature/T7-tide-table\n",
    _resolve("feature/T7-tide-table"): f"{TASK_HEAD}\n",
    _resolve("main"): f"{MAIN_HEAD}\n",
    _resolve(TASK_HEAD): f"{TASK_HEAD}\n",
    _resolve(MERGE_BASE): f"{MERGE_BASE}\n",
    ("git", "merge-base", "--end-of-options", MAIN_HEAD, TASK_HEAD): f"{MERGE_BASE}\n",
    ("git", "merge-base", "--is-ancestor"): "",
    ("git", "diff", "--numstat"): "1\t0\tsrc/tides.py\n",
    ("git", "diff"): "+def tide():\n",
    ("awawa", "diff"): '{"added": [], "changed": [], "removed": []}',
    ("awawa", "context"): "TASK T7\n",
    ("awawa", "lint"): "",
    ("awawa", "fmt"): "",
}


class RefusingForgeResolverDouble:
    def __call__(self, kind: str, name: str, **places):
        raise AssertionError(f"the command resolved the {kind} {name}")


class VerifyContextOfATaskWithoutAForgeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        for ref in (TASK_HEAD, MERGE_BASE):
            (self.root / "cache" / "refs" / "tidepool" / ref).mkdir(parents=True)
        write_ledger(self.root, [WAVE_STARTED])
        corpus = {"PROJECT": {"tidepool": LOCAL_PROJECT}, "TASK": {"T7": ()}, "POLICY": {}}
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double(corpus, LOCAL_TASK_WORKTREE),
            resolve_plugin=RefusingForgeResolverDouble(),
        )
        self.no_pull_request = None

    def test_should_judge_the_head_of_the_task_branch_with_no_pull_request(self):
        # Act
        document = COMMAND.run(Namespace(pr=self.no_pull_request), self.runtime)

        # Assert
        self.assertEqual(document["project"], "tidepool")
        self.assertIsNone(document["pr"])
        self.assertEqual(document["task"], "T7")
        self.assertEqual(document["head"], TASK_HEAD)

    def test_should_print_the_diff_of_the_task_branch_from_its_merge_base_with_the_branch_of_its_milestone(self):
        # Act
        document = COMMAND.run(Namespace(pr=self.no_pull_request), self.runtime)

        # Assert
        self.assertEqual(
            document["diff"],
            {"command": f"git diff {MERGE_BASE} {TASK_HEAD}", "exit_code": 0, "stderr": "", "output": "+def tide():\n"},
        )
