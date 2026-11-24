import argparse
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.add_command_parsers import add_command_parsers
from brigade.commands.review_context import COMMAND
from brigade.errors import BrigadeError
from brigade.system.run_process import ProcessRecord
from tests.unit.captures.take_screenshot import take_screenshot
from tests.unit.captures.take_screenshots_or import take_screenshots_or
from tests.unit.commands.command_runtime import (
    answer,
    answer_from_corpus,
    create_machine_double,
    create_outputs_double,
    create_worktrees_double,
    write_ledger,
    write_operational_corpus,
)
from tests.unit.commands.run_directories import create_run_record
from tests.unit.commands.test_preflight import (
    M4_BRANCH_CUT,
    TASK_PR_OPENED,
    TASK_WORKTREE,
    TIDEPOOL_PROJECT,
    TIDEPOOL_TASKS,
    WAVE_STARTED,
    ForgeDeclineDouble,
)
from tests.unit.create_preflight_plugins import resolve_preflight_kinds_or
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble

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
FAILED_CHECK = {"result": "fail", "name": "scope", "findings": ["brigade/cli.py is outside the task"]}


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
GOAL = {
    "task": "T7",
    "title": "Print the tide table of the week",
    "milestone": {
        "name": "M4",
        "title": "Tide tables",
        "subject": "print the tide tables of a harbour",
        "desc": ["a sailor reads the tides of the week at a glance"],
        "source": ["the user's words: I want the tides of the week on one page"],
    },
}
MOCKUP = {
    "reference": "artifact/harbour/index.html",
    "covers": "tides",
    "revises": None,
    "reads": None,
    "refusal": None,
    "captures": {
        "delivered": [
            "/state/captures/oak/T7/tides-delivered-01.png",
            "/state/captures/oak/T7/tides-delivered-02.png",
        ],
        "reference": ["/state/captures/oak/T7/tides-reference-01.png"],
    },
}


def create_document(rules: list[dict] | None, previous: dict | None = None, repair: dict | None = None) -> dict:
    return {
        "pr": 42,
        "task": "T7",
        "head": "8885daa",
        "context": [AWAWA_CONTEXT],
        "goal": GOAL,
        "references": [MOCKUP],
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
            "# goal\ntask T7: Print the tide table of the week\n"
            "milestone M4: Tide tables\n"
            "  subject: print the tide tables of a harbour\n"
            "  desc: a sailor reads the tides of the week at a glance\n"
            "  source: the user's words: I want the tides of the week on one page\n\n"
            "# reference\nartifact/harbour/index.html\n"
            "  covers: tides\n"
            "  delivered 1/2: /state/captures/oak/T7/tides-delivered-01.png\n"
            "  delivered 2/2: /state/captures/oak/T7/tides-delivered-02.png\n"
            "  reference page 1/1: /state/captures/oak/T7/tides-reference-01.png\n\n"
            "# diff\n$ git diff 0000000 8885daa\nexit 0\n+def tide():\n\n"
            "# preflight\nfail  scope\n  brigade/cli.py is outside the task\n\n"
            "# rules\n$ awawa context @TRIGGER.python_file\nexit 0\nRULE pure\n\n"
            "# grades\ncritical\nhigh\nmedium\nlow",
        )

    def test_should_say_why_a_task_revises_its_reference_and_what_to_read_for_a_section_no_page_renders(self):
        # Arrange
        foundation = {
            "reference": "artifact/harbour/index.html",
            "covers": "foundation",
            "revises": "the task draws the foundation itself",
            "reads": "harbour/static/harbour.css",
            "refusal": None,
            "captures": None,
        }
        document = {**create_document(RULES), "references": [foundation]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn(
            "# reference\nartifact/harbour/index.html\n"
            "  covers: foundation\n"
            "  revises: the task draws the foundation itself\n"
            "  read: harbour/static/harbour.css, the section judged by reading this file, no PNG pair\n\n",
            text,
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
            "# goal\ntask T7: Print the tide table of the week\n"
            "milestone M4: Tide tables\n"
            "  subject: print the tide tables of a harbour\n"
            "  desc: a sailor reads the tides of the week at a glance\n"
            "  source: the user's words: I want the tides of the week on one page\n\n"
            "# reference\nartifact/harbour/index.html\n"
            "  covers: tides\n"
            "  delivered 1/2: /state/captures/oak/T7/tides-delivered-01.png\n"
            "  delivered 2/2: /state/captures/oak/T7/tides-delivered-02.png\n"
            "  reference page 1/1: /state/captures/oak/T7/tides-reference-01.png\n\n"
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

    def test_should_say_that_a_task_of_no_milestone_serves_its_own_title(self):
        # Arrange
        document = {
            **create_document(RULES),
            "goal": {"task": "T9", "title": "Fix the harbour name", "milestone": None},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn(
            "# goal\ntask T9: Fix the harbour name\nno milestone: the title of the task is its goal\n\n", text
        )

    def test_should_print_none_where_the_milestone_states_no_subject(self):
        # Arrange
        milestone = {"name": "M4", "title": "Tide tables", "subject": None, "desc": [], "source": []}
        document = {**create_document(RULES), "goal": {**GOAL, "milestone": milestone}}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn("milestone M4: Tide tables\n  subject: none\n\n", text)

    def test_should_print_none_under_the_reference_of_a_task_citing_none(self):
        # Arrange
        no_reference = []
        document = {**create_document(RULES), "references": no_reference}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn("# reference\nnone\n\n", text)

    def test_should_print_none_where_a_reference_states_no_coverage(self):
        # Arrange
        uncovered = {
            "reference": "artifact/harbour/index.html",
            "covers": None,
            "revises": None,
            "reads": None,
            "refusal": None,
            "captures": None,
        }
        document = {**create_document(RULES), "references": [uncovered]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn("# reference\nartifact/harbour/index.html\n  covers: none\n", text)


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
        options = parser.parse_args(["review", "context"])

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
            resolve_plugin=resolve_preflight_kinds_or(lambda kind, name, **places: self.forge),
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
        (self.root / "cache" / "refs" / "tidepool" / TASK_HEAD).mkdir(parents=True)
        (self.root / "cache" / "refs" / "tidepool" / MERGE_BASE).mkdir(parents=True)
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


class VerifyContextFromTheDisposableWorktreeOfAReadingRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / TASK_HEAD).mkdir(parents=True)
        (self.root / "cache" / "refs" / "tidepool" / MERGE_BASE).mkdir(parents=True)
        write_ledger(self.root, [WAVE_STARTED])
        run_directory = self.root / "state" / "runs" / "20261111T090000Z-e10d04"
        run_directory.mkdir(parents=True)
        disposable_worktree = str(run_directory / "worktree")
        record = {
            **create_run_record("20261111T090000Z-e10d04", "tidepool_w16", "T7"),
            "slot": "review",
            "cwd": "/srv/tidepool-T7",
            "worktree": disposable_worktree,
        }
        (run_directory / "run.json").write_text(json.dumps(record), encoding="utf-8")
        detached = {
            ("git", "rev-parse", "--show-toplevel"): f"{disposable_worktree}\n",
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): "/srv/tidepool/.git\n",
            ("git", "branch", "--show-current"): "\n",
        }
        corpus = {"PROJECT": {"tidepool": LOCAL_PROJECT}, "TASK": {"T7": ()}, "POLICY": {}}
        self.runtime = create_test_runtime(
            create_test_paths(self.root, run_directory=run_directory),
            run_process=create_worktrees_double(
                corpus,
                {str(Path.cwd()): detached, disposable_worktree: detached},
                LOCAL_TASK_WORKTREE,
            ),
            resolve_plugin=RefusingForgeResolverDouble(),
        )
        self.no_pull_request = None

    def test_should_judge_the_task_of_the_worktree_the_run_was_cut_from(self):
        # Act
        document = COMMAND.run(Namespace(pr=self.no_pull_request), self.runtime)

        # Assert
        self.assertEqual(document["task"], "T7")


class VerifyContextOfAReferenceTest(unittest.TestCase):
    def test_should_print_a_reference_that_is_a_url_refused_with_why(self):
        # Arrange
        refused = {
            "reference": "https://example.org/harbour",
            "covers": "tides",
            "revises": None,
            "reads": None,
            "refusal": "a REFERENCE is a repository path: the review cannot open a URL",
            "captures": None,
        }
        document = {**create_document(RULES), "references": [refused]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn(
            "# reference\nhttps://example.org/harbour\n  covers: tides\n"
            "  refused: a REFERENCE is a repository path: the review cannot open a URL\n\n",
            text,
        )

    def test_should_say_that_no_png_pair_was_captured_for_a_page(self):
        # Arrange
        uncaptured = {
            "reference": "artifact/harbour/index.html",
            "covers": "tides",
            "revises": None,
            "reads": None,
            "refusal": None,
            "captures": None,
        }
        document = {**create_document(RULES), "references": [uncaptured]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn(
            "# reference\nartifact/harbour/index.html\n  covers: tides\n"
            "  captures: none at this head, brigade build capture wrote no PNG pair for this page\n\n",
            text,
        )

    def test_should_say_under_the_goal_that_the_head_defines_no_task(self):
        # Arrange
        document = {**create_document(RULES), "goal": None, "references": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertIn("# goal\nthe head defines no @TASK.T7: the preflight promotion says so\n\n", text)


TASK_BRANCH = "task/M4-tides/T7"
MILESTONE_HEAD = "4c1d2e0"
RECIPES_OF_THE_CORPUS = json.dumps({"entities": [{"type": "RECIPE", "name": "capture"}]})
CAPTURE_RECIPE = json.dumps(
    {
        "name": "capture",
        "fields": [
            {"name": "SCHEMA_VERSION", "atoms": ['"1"'], "fields": []},
            {"name": "DESC", "atoms": ['"a page of the harbour as delivered"'], "fields": []},
            {
                "name": "STEP",
                "atoms": ['"command"'],
                "fields": [
                    {"name": "ARGV", "atoms": ['"tidepool"'], "fields": []},
                    {"name": "ARGV", "atoms": ['"render"'], "fields": []},
                    {"name": "ARGV", "atoms": ['"{page}"'], "fields": []},
                ],
            },
        ],
    }
)
HARBOUR_REFERENCE = '<html><head></head><body><section id="tides" hidden>tides</section></body></html>'
HARBOUR_TIDES = {
    "name": "REFERENCE",
    "atoms": ['"artifact/harbour/index.html"'],
    "fields": [{"name": "COVERS", "atoms": ['"tides"'], "fields": []}],
}
TASK_CITING_THE_HARBOUR = json.dumps(
    {"fields": [{"name": "MILESTONE", "atoms": ['"@MILESTONE.M4"'], "fields": []}, HARBOUR_TIDES]}
)
TASK_OF_NO_MILESTONE_CITING_THE_HARBOUR = json.dumps({"fields": [HARBOUR_TIDES]})
BODY_AT_THE_FIRST_HEAD = (
    "Delivers @TASK.T7.\n\n## Captures\n\nEach page the task covers at efd5ed1.\n\n"
    "| Page | Delivered | Reference |\n|---|---|---|\n| tides | `d0` | `r0` |\n\n"
    "Co-Authored-By: Fake Client <fake@example.org>\n"
)


def _host_in_a_gist(request: dict) -> dict:
    return {"schema_version": 1, "urls": ["https://gist.example/delivered.png", "https://gist.example/reference.png"]}


class VerifyContextOfAPullRequestCitingAReferenceTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(
            '[forge_accounts]\ncli = "octo-cli"\nbuild = "octo-bot"\n', encoding="utf-8"
        )
        write_ledger(self.root, [M4_BRANCH_CUT, WAVE_STARTED, TASK_PR_OPENED])
        (self.root / "cache" / "refs" / "tidepool" / TASK_HEAD).mkdir(parents=True)
        (self.root / "cache" / "refs" / "tidepool" / MERGE_BASE).mkdir(parents=True)
        self.head_tree = self.root / "cache" / "refs" / "tidepool" / TASK_HEAD
        self.base_tree = self.root / "cache" / "refs" / "tidepool" / MERGE_BASE
        self.worktree = self.root / "tidepool-T7"
        (self.worktree / "artifact" / "harbour").mkdir(parents=True)
        (self.worktree / "artifact" / "harbour" / "index.html").write_text(HARBOUR_REFERENCE)
        self.forge = ForgeDouble(
            {
                "read_login_environment": lambda request: {
                    "schema_version": 1,
                    "environment": {"GH_TOKEN": f"token-of-{request['login']}"},
                },
                "read_pull_request": lambda request: {
                    "schema_version": 1,
                    "pull_request": {
                        "number": 42,
                        "title": "feat(tides): print the tide table of the week",
                        "body": BODY_AT_THE_FIRST_HEAD,
                        "head": TASK_BRANCH,
                        "head_sha": TASK_HEAD,
                        "checks": [{"name": "unit", "conclusion": "success"}],
                    },
                },
                "read_repository_visibility": lambda request: {"schema_version": 1, "public": True},
                "host_images": _host_in_a_gist,
                "rewrite_pull_request_body": lambda request: {"schema_version": 1},
            }
        )
        outputs = {
            **LOCAL_TASK_WORKTREE,
            ("git", "rev-parse", "--show-toplevel"): f"{self.worktree}\n",
            _resolve("HEAD"): f"{TASK_HEAD}\n",
            _resolve("refs/remotes/origin/integration/M4-tides"): f"{MILESTONE_HEAD}\n",
            ("git", "merge-base", "--end-of-options", MILESTONE_HEAD, TASK_HEAD): f"{MERGE_BASE}\n",
            ("awawa", "show", "@TASK.T7", "--json", str(self.worktree)): TASK_CITING_THE_HARBOUR,
            ("awawa", "show", "@TASK.T7", "--json", str(self.head_tree)): TASK_CITING_THE_HARBOUR,
            ("awawa", "show", "@TASK.T7", "--json", str(self.base_tree)): TASK_CITING_THE_HARBOUR,
            ("awawa", "status", "--json", str(self.worktree)): RECIPES_OF_THE_CORPUS,
            ("awawa", "show", "@RECIPE.capture", "--json", str(self.worktree)): CAPTURE_RECIPE,
            ("tidepool", "render", "tides"): "<html><body>the tides as delivered</body></html>",
            ("git", "fetch"): "",
        }
        entities = {
            "PROJECT": {"tidepool": GITHUB_PROJECT},
            "TASK": TIDEPOOL_TASKS,
            "MILESTONE": {"M4": (("TITLE", "Tide tables"),)},
        }
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=take_screenshots_or(create_machine_double(entities, outputs)),
            resolve_plugin=resolve_preflight_kinds_or(lambda kind, name, **places: self.forge),
        )

    def test_should_put_the_captures_of_the_head_in_the_body_as_the_build_account(self):
        # Act
        COMMAND.run(Namespace(pr=42), self.runtime)

        # Assert
        self.assertEqual(
            self.forge.list_requests("rewrite_pull_request_body"),
            [
                {
                    "repository": str(self.worktree),
                    "number": 42,
                    "environment": {"GH_TOKEN": "token-of-octo-bot"},
                    "body": "Delivers @TASK.T7.\n\n## Captures\n\n"
                    f"Each page the task covers at {TASK_HEAD}, delivered beside its reference. "
                    "The repository is public: the images are public too, in a gist of the machine account.\n\n"
                    "| Page | Delivered | Reference |\n|---|---|---|\n"
                    "| tides | ![tides delivered](https://gist.example/delivered.png)"
                    " | ![tides reference](https://gist.example/reference.png) |\n"
                    "\nCo-Authored-By: Fake Client <fake@example.org>\n",
                }
            ],
        )


def _answer_as_the_machine_taking_screenshots(request) -> ProcessRecord:
    if request.argv[0] == "firefox":
        take_screenshot(request)
        return answer(request, "")
    return answer_from_corpus({"PROJECT": {"tidepool": LOCAL_PROJECT}, "POLICY": {}}, request)


class VerifyContextOfATaskWithoutAForgeCitingAReferenceTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / TASK_HEAD).mkdir(parents=True)
        (self.root / "cache" / "refs" / "tidepool" / MERGE_BASE).mkdir(parents=True)
        head_tree = self.root / "cache" / "refs" / "tidepool" / TASK_HEAD
        write_ledger(self.root, [WAVE_STARTED])
        self.worktree = self.root / "tidepool-T7"
        (self.worktree / "artifact" / "harbour").mkdir(parents=True)
        (self.worktree / "artifact" / "harbour" / "index.html").write_text(HARBOUR_REFERENCE)
        outputs = {
            **LOCAL_TASK_WORKTREE,
            ("git", "rev-parse", "--show-toplevel"): f"{self.worktree}\n",
            _resolve("HEAD"): f"{TASK_HEAD}\n",
            (
                "awawa",
                "show",
                "@TASK.T7",
                "--json",
                str(self.worktree),
            ): TASK_OF_NO_MILESTONE_CITING_THE_HARBOUR,
            ("awawa", "show", "@TASK.T7", "--json", str(head_tree)): TASK_OF_NO_MILESTONE_CITING_THE_HARBOUR,
            ("awawa", "status", "--json", str(self.worktree)): RECIPES_OF_THE_CORPUS,
            ("awawa", "show", "@RECIPE.capture", "--json", str(self.worktree)): CAPTURE_RECIPE,
            ("tidepool", "render", "tides"): f"<html><body>{self.root}/home/tides</body></html>",
        }
        self.paths = create_test_paths(self.root)
        self.runtime = create_test_runtime(
            self.paths,
            run_process=create_outputs_double(outputs, _answer_as_the_machine_taking_screenshots),
            resolve_plugin=RefusingForgeResolverDouble(),
        )
        self.no_pull_request = None

    def test_should_name_the_png_pair_it_captured_at_the_head_of_the_task_branch(self):
        # Act
        document = COMMAND.run(Namespace(pr=self.no_pull_request), self.runtime)

        # Assert
        captures = self.paths.state_root / "captures" / "tidepool" / "T7" / TASK_HEAD
        self.assertEqual(
            document["references"],
            [
                {
                    "reference": "artifact/harbour/index.html",
                    "covers": "tides",
                    "revises": None,
                    "reads": None,
                    "refusal": None,
                    "captures": {
                        "delivered": [str(captures / "tides-delivered-01.png")],
                        "reference": [str(captures / "tides-reference-01.png")],
                    },
                }
            ],
        )

    def test_should_show_the_home_directory_as_a_tilde_in_the_page_it_captured(self):
        # Act
        COMMAND.run(Namespace(pr=self.no_pull_request), self.runtime)

        # Assert
        captures = self.paths.state_root / "captures" / "tidepool" / "T7" / TASK_HEAD
        self.assertEqual((captures / "tides-delivered.html").read_text(), "<html><body>~/tides</body></html>")


TASK_OF_NO_MILESTONE_READING_A_FILE_FOR_THE_HARBOUR = json.dumps(
    {
        "fields": [
            {
                **HARBOUR_TIDES,
                "fields": [*HARBOUR_TIDES["fields"], {"name": "READ", "atoms": ['"src/tides.css"'], "fields": []}],
            }
        ]
    }
)


class VerifyContextOfATaskWhoseBranchWritesReadTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / TASK_HEAD).mkdir(parents=True)
        (self.root / "cache" / "refs" / "tidepool" / MERGE_BASE).mkdir(parents=True)
        head_tree = self.root / "cache" / "refs" / "tidepool" / TASK_HEAD
        base_tree = self.root / "cache" / "refs" / "tidepool" / MERGE_BASE
        write_ledger(self.root, [WAVE_STARTED])
        worktree = self.root / "tidepool-T7"
        (worktree / "artifact" / "harbour").mkdir(parents=True)
        (worktree / "artifact" / "harbour" / "index.html").write_text(HARBOUR_REFERENCE)
        outputs = {
            **LOCAL_TASK_WORKTREE,
            ("git", "rev-parse", "--show-toplevel"): f"{worktree}\n",
            _resolve("HEAD"): f"{TASK_HEAD}\n",
            ("awawa", "show", "@TASK.T7", "--json", str(worktree)): TASK_OF_NO_MILESTONE_READING_A_FILE_FOR_THE_HARBOUR,
            (
                "awawa",
                "show",
                "@TASK.T7",
                "--json",
                str(head_tree),
            ): TASK_OF_NO_MILESTONE_READING_A_FILE_FOR_THE_HARBOUR,
            ("awawa", "show", "@TASK.T7", "--json", str(base_tree)): TASK_OF_NO_MILESTONE_CITING_THE_HARBOUR,
            ("awawa", "status", "--json", str(worktree)): RECIPES_OF_THE_CORPUS,
            ("awawa", "show", "@RECIPE.capture", "--json", str(worktree)): CAPTURE_RECIPE,
            ("tidepool", "render", "tides"): "<html><body>tides</body></html>",
        }
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_outputs_double(outputs, _answer_as_the_machine_taking_screenshots),
            resolve_plugin=RefusingForgeResolverDouble(),
        )

    def test_should_judge_the_task_against_its_reference_as_the_base_of_its_branch_ratified_it(self):
        # Arrange
        no_pull_request = None

        # Act
        document = COMMAND.run(Namespace(pr=no_pull_request), self.runtime)

        # Assert
        self.assertIsNone(document["references"][0]["reads"])


LOCAL_AREA_PROJECT = (*LOCAL_PROJECT, ("MODE", "area"), ("CORPUS", "corpus"))


def _answer_for_an_area_taking_screenshots(request) -> ProcessRecord:
    if request.argv[0] == "firefox":
        take_screenshot(request)
        return answer(request, "")
    return answer_from_corpus({"PROJECT": {"tidepool": LOCAL_AREA_PROJECT}, "POLICY": {}}, request)


class VerifyContextOfATaskOfACorpusAreaCitingAReferenceTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        (self.root / "cache" / "refs" / "tidepool" / TASK_HEAD / "corpus").mkdir(parents=True)
        (self.root / "cache" / "refs" / "tidepool" / MERGE_BASE / "corpus").mkdir(parents=True)
        head_area = self.root / "cache" / "refs" / "tidepool" / TASK_HEAD / "corpus"
        write_ledger(self.root, [WAVE_STARTED])
        self.worktree = self.root / "tidepool-T7"
        (self.worktree / "artifact" / "harbour").mkdir(parents=True)
        (self.worktree / "artifact" / "harbour" / "index.html").write_text(HARBOUR_REFERENCE)
        area = self.worktree / "corpus"
        outputs = {
            **LOCAL_TASK_WORKTREE,
            ("git", "rev-parse", "--show-toplevel"): f"{self.worktree}\n",
            _resolve("HEAD"): f"{TASK_HEAD}\n",
            ("awawa", "show", "@TASK.T7", "--json", str(area)): TASK_OF_NO_MILESTONE_CITING_THE_HARBOUR,
            ("awawa", "show", "@TASK.T7", "--json", str(head_area)): TASK_OF_NO_MILESTONE_CITING_THE_HARBOUR,
            ("awawa", "status", "--json", str(area)): RECIPES_OF_THE_CORPUS,
            ("awawa", "show", "@RECIPE.capture", "--json", str(area)): CAPTURE_RECIPE,
            ("tidepool", "render", "tides"): "<html><body>tides</body></html>",
        }
        self.paths = create_test_paths(self.root)
        self.runtime = create_test_runtime(
            self.paths,
            run_process=create_outputs_double(outputs, _answer_for_an_area_taking_screenshots),
            resolve_plugin=RefusingForgeResolverDouble(),
        )

    def test_should_capture_the_pages_the_task_of_the_area_covers(self):
        # Act
        document = COMMAND.run(Namespace(pr=None), self.runtime)

        # Assert
        captures = self.paths.state_root / "captures" / "tidepool" / "T7" / TASK_HEAD
        self.assertEqual(
            document["references"][0]["captures"],
            {
                "delivered": [str(captures / "tides-delivered-01.png")],
                "reference": [str(captures / "tides-reference-01.png")],
            },
        )
