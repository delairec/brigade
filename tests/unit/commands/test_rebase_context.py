import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.rebase_context import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner, create_corpus_double, write_ledger
from tests.unit.commands.test_verify_preflight import (
    M4_BRANCH_CUT,
    TASK_PR_OPENED,
    TIDEPOOL_PROJECT,
    TIDEPOOL_TASKS,
    WAVE_STARTED,
)

MERGE_TREE = (
    "git",
    "merge-tree",
    "--write-tree",
    "--name-only",
    "--no-messages",
    "HEAD",
    "origin/integration/M4-tides",
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NO_RED_HEAD = None
NO_MAIN_REPAIR = None
CONFLICTING_MERGE = ProcessAnswer(stdout="4b825dc\nsrc/tides.py\nREADME.md\n", exit_code=1)
CLEAN_MERGE = ProcessAnswer(stdout="4b825dc\n")


TASK_BRANCH = "feature/T7-chart-the-tides"
TASK_PR_OPENED_ON_ITS_BRANCH = {**TASK_PR_OPENED, "branch": TASK_BRANCH}
TASK_OF_NO_MILESTONE = {"T7": ()}


def create_document(conflicts: list[str]) -> dict:
    return {
        "schema_version": 1,
        "project": "tidepool",
        "pr": 42,
        "task": "T7",
        "branch": "feature/T7-chart-the-tides",
        "base": "integration/M4-tides",
        "conflicts": conflicts,
    }


class RebaseContextTextTest(unittest.TestCase):
    def test_should_print_the_branch_its_base_and_each_conflicting_file(self):
        # Arrange
        document = create_document(["src/tides.py", "README.md"])

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "# branch\nfeature/T7-chart-the-tides\n\n# base\nintegration/M4-tides\n\n# conflicts\nsrc/tides.py\nREADME.md",
        )


class RebaseContextOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [M4_BRANCH_CUT, WAVE_STARTED, TASK_PR_OPENED_ON_ITS_BRANCH])

    def _create_runtime(self, merge: ProcessAnswer, tasks: dict = TIDEPOOL_TASKS, base: str = "integration/M4-tides"):
        answers = {
            ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout="/srv/tidepool-T7\n"),
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                stdout="/srv/tidepool/.git\n"
            ),
            (*MERGE_TREE[:-1], f"origin/{base}"): merge,
        }
        corpus = {"PROJECT": {"tidepool": (*TIDEPOOL_PROJECT, ("MAIN", "main"))}, "TASK": tasks}
        machine = ScriptedProcessRunner(answers, fallback=create_corpus_double(corpus))
        return create_test_runtime(create_test_paths(self.root), run_process=machine.run)

    def test_should_give_the_files_git_reports_in_conflict_between_the_branch_and_its_base(self):
        for case, merge, conflicts in [
            ("two files in conflict", CONFLICTING_MERGE, ["src/tides.py", "README.md"]),
            ("no file in conflict", CLEAN_MERGE, []),
        ]:
            with self.subTest(case=case):
                # Arrange
                runtime = self._create_runtime(merge)

                # Act
                document = COMMAND.run(Namespace(pr=42, head=NO_RED_HEAD, into=NO_MAIN_REPAIR), runtime)

                # Assert
                self.assertEqual(document, create_document(conflicts))

    def test_should_take_main_as_the_base_of_a_task_naming_no_milestone(self):
        # Arrange
        runtime = self._create_runtime(CLEAN_MERGE, tasks=TASK_OF_NO_MILESTONE, base="main")

        # Act
        document = COMMAND.run(Namespace(pr=42, head=NO_RED_HEAD, into=NO_MAIN_REPAIR), runtime)

        # Assert
        self.assertEqual(document["base"], "main")


WITHOUT_FORGE = (("PATH", "/srv/tidepool"),)
ON_GITHUB = (("PATH", "/srv/tidepool"), ("FORGE", "github"))
NO_PULL_REQUEST = None


class RebaseContextOfATaskWithoutAPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [M4_BRANCH_CUT, WAVE_STARTED])

    def _create_runtime(self, project: tuple, base: str):
        answers = {
            ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout="/srv/tidepool-T7\n"),
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                stdout="/srv/tidepool/.git\n"
            ),
            ("git", "branch", "--show-current"): ProcessAnswer(stdout=f"{TASK_BRANCH}\n"),
            ("git", "fetch", "--quiet", "origin", "integration/M4-tides"): ProcessAnswer(),
            (*MERGE_TREE[:-1], base): CONFLICTING_MERGE,
        }
        corpus = {"PROJECT": {"tidepool": project}, "TASK": TIDEPOOL_TASKS}
        machine = ScriptedProcessRunner(answers, fallback=create_corpus_double(corpus))
        return create_test_runtime(create_test_paths(self.root), run_process=machine.run)

    def test_should_read_the_task_from_the_branch_of_the_worktree_and_its_conflicts_with_its_milestone_branch(self):
        for case, project, base in [
            ("a project without a forge", WITHOUT_FORGE, "integration/M4-tides"),
            ("a project on GitHub", ON_GITHUB, "origin/integration/M4-tides"),
        ]:
            with self.subTest(case=case):
                # Arrange
                runtime = self._create_runtime(project, base)

                # Act
                document = COMMAND.run(Namespace(pr=NO_PULL_REQUEST, head=NO_RED_HEAD, into=NO_MAIN_REPAIR), runtime)

                # Assert
                self.assertEqual(
                    document,
                    {
                        "schema_version": 1,
                        "project": "tidepool",
                        "pr": None,
                        "task": "T7",
                        "branch": "feature/T7-chart-the-tides",
                        "base": "integration/M4-tides",
                        "conflicts": ["src/tides.py", "README.md"],
                    },
                )


TIDES_BRANCH_CUT = {
    "schema_version": 1,
    "ts": "2026-09-29T22:00:00Z",
    "event": "milestone.branch_cut",
    "project": "tidepool",
    "milestone": "M4",
    "branch": "integration/tides",
    "login": "brigade-bot",
}
MILESTONE_WITHOUT_FORGE = (("PATH", "/srv/tidepool"), ("MAIN", "main"))
MILESTONE_ON_GITHUB = (("PATH", "/srv/tidepool"), ("MAIN", "main"), ("FORGE", "github"))
TASK_OF_THE_MILESTONE = (("MILESTONE", "@MILESTONE.M4"),)
HARDENING_BRANCH_CUT = {**TIDES_BRANCH_CUT, "milestone": "M6", "branch": "integration/hardening-the-tick"}
WAVE_STARTED_ON_A_BRANCH = {**WAVE_STARTED, "branch": "integration/tidepool_w16"}


class RebaseContextOfAMilestoneOrWaveBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [TIDES_BRANCH_CUT, HARDENING_BRANCH_CUT, WAVE_STARTED_ON_A_BRANCH])

    def _create_runtime(self, project: tuple, branch: str, base: str):
        answers = {
            ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout="/srv/tidepool-branch\n"),
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                stdout="/srv/tidepool/.git\n"
            ),
            ("git", "branch", "--show-current"): ProcessAnswer(stdout=f"{branch}\n"),
            ("git", "fetch", "--quiet", "origin"): ProcessAnswer(),
            (*MERGE_TREE[:-1], base): CONFLICTING_MERGE,
        }
        corpus = {"PROJECT": {"tidepool": project}, "TASK": {"T7": TASK_OF_THE_MILESTONE}}
        machine = ScriptedProcessRunner(answers, fallback=create_corpus_double(corpus))
        return create_test_runtime(create_test_paths(self.root), run_process=machine.run)

    def test_should_describe_the_branch_its_base_and_its_conflicts_with_that_base(self):
        for case, project, branch, base, upstream in [
            ("a milestone branch without a forge", MILESTONE_WITHOUT_FORGE, "integration/tides", "main", "main"),
            ("a milestone branch on GitHub", MILESTONE_ON_GITHUB, "integration/tides", "main", "origin/main"),
            (
                "a milestone branch whose slug holds a hyphen",
                MILESTONE_WITHOUT_FORGE,
                "integration/hardening-the-tick",
                "main",
                "main",
            ),
            (
                "a wave branch recorded before waves had none",
                MILESTONE_WITHOUT_FORGE,
                "integration/tidepool_w16",
                "integration/tides",
                "integration/tides",
            ),
            (
                "a wave branch recorded before waves had none, on GitHub",
                MILESTONE_ON_GITHUB,
                "integration/tidepool_w16",
                "integration/tides",
                "origin/integration/tides",
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                runtime = self._create_runtime(project, branch, upstream)

                # Act
                document = COMMAND.run(Namespace(pr=NO_PULL_REQUEST, head=NO_RED_HEAD, into=NO_MAIN_REPAIR), runtime)

                # Assert
                self.assertEqual(
                    document,
                    {
                        "schema_version": 1,
                        "project": "tidepool",
                        "pr": None,
                        "task": None,
                        "branch": branch,
                        "base": base,
                        "conflicts": ["src/tides.py", "README.md"],
                    },
                )

    def test_should_refuse_a_branch_that_is_neither_a_task_a_wave_nor_a_milestone_branch(self):
        # Arrange
        runtime = self._create_runtime(MILESTONE_WITHOUT_FORGE, "feature/tides", "main")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pr=NO_PULL_REQUEST, head=NO_RED_HEAD, into=NO_MAIN_REPAIR), runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "the branch feature/tides is not a task, a wave or a milestone branch of @PROJECT.tidepool",
        )

    def test_should_refuse_a_milestone_or_wave_branch_another_project_recorded(self):
        for case, recorded, branch in [
            ("a milestone branch", {**TIDES_BRANCH_CUT, "project": "depot"}, "integration/tides"),
            ("a wave branch", {**WAVE_STARTED_ON_A_BRANCH, "project": "depot"}, "integration/tidepool_w16"),
        ]:
            with self.subTest(case=case):
                # Arrange
                write_ledger(self.root, [recorded])
                runtime = self._create_runtime(MILESTONE_WITHOUT_FORGE, branch, "main")

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    COMMAND.run(Namespace(pr=NO_PULL_REQUEST, head=NO_RED_HEAD, into=NO_MAIN_REPAIR), runtime)

                # Assert
                self.assertEqual(
                    str(raised.exception),
                    f"the branch {branch} is not a task, a wave or a milestone branch of @PROJECT.tidepool",
                )


RED_HEAD = "c0ffee1"
RESOLVE_RED_HEAD = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "c0ffee1^{commit}")


class CheckRunsByBranchForgeDouble:
    def __init__(self, check_runs_by_branch: dict):
        self.check_runs_by_branch = check_runs_by_branch

    def list_check_runs(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "check_runs": self.check_runs_by_branch.get(request["branch"], [])}


class RebaseContextOfARedHeadTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")

    def _create_runtime(self, project: tuple, branch: str, forge: object = None):
        answers = {
            ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout="/srv/tidepool-branch\n"),
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                stdout="/srv/tidepool/.git\n"
            ),
            ("git", "branch", "--show-current"): ProcessAnswer(stdout=f"{branch}\n"),
            RESOLVE_RED_HEAD: ProcessAnswer(stdout=f"{RED_HEAD}\n"),
        }
        corpus = {"PROJECT": {"tidepool": project}}
        machine = ScriptedProcessRunner(answers, fallback=create_corpus_double(corpus))
        return create_test_runtime(
            create_test_paths(self.root), run_process=machine.run, resolve_plugin=lambda kind, name: forge
        )

    def test_should_name_the_milestone_branch_repaired_in_place_its_red_commit_and_the_command_that_failed(self):
        # Arrange
        record = self.root / "state" / "commit-checks" / "tidepool" / f"{RED_HEAD}.json"
        record.parent.mkdir(parents=True)
        record.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project": "tidepool",
                    "commit": RED_HEAD,
                    "checks": [{"command": "make setup", "exit_code": 0}, {"command": "make test", "exit_code": 2}],
                }
            ),
            encoding="utf-8",
        )
        runtime = self._create_runtime(MILESTONE_WITHOUT_FORGE, "integration/tides")

        # Act
        document = COMMAND.run(Namespace(pr=NO_PULL_REQUEST, head=RED_HEAD, into=NO_MAIN_REPAIR), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": "tidepool",
                "pr": None,
                "task": None,
                "branch": "integration/tides",
                "head": "c0ffee1",
                "into": None,
                "failed": ["make test"],
            },
        )

    def test_should_name_the_fix_branch_of_the_main_branch_its_red_commit_and_the_check_run_that_failed_on_main(self):
        # Arrange
        forge = CheckRunsByBranchForgeDouble(
            {
                "main": [
                    {"name": "ci / tests", "conclusion": "failure", "head": "c0ffee1"},
                    {"name": "ci / lint", "conclusion": "success", "head": "c0ffee1"},
                ]
            }
        )
        runtime = self._create_runtime(MILESTONE_ON_GITHUB, "fix/repair-main-c0ffee1", forge)

        # Act
        document = COMMAND.run(Namespace(pr=NO_PULL_REQUEST, head=RED_HEAD, into="main"), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": "tidepool",
                "pr": None,
                "task": None,
                "branch": "fix/repair-main-c0ffee1",
                "head": "c0ffee1",
                "into": "main",
                "failed": ["ci / tests"],
            },
        )


class RebaseContextTextOfARedHeadTest(unittest.TestCase):
    def test_should_print_the_branch_its_red_commit_and_each_command_that_failed(self):
        for case, into, text in [
            (
                "a branch repaired in place",
                None,
                "# branch\nintegration/tides\n\n# head\nc0ffee1\n\n# failed\nmake test\nmake lint",
            ),
            (
                "the main branch repaired on a fix branch",
                "main",
                "# branch\nintegration/tides\n\n# head\nc0ffee1\n\n# into\nmain\n\n# failed\nmake test\nmake lint",
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                document = {
                    "schema_version": 1,
                    "project": "tidepool",
                    "pr": None,
                    "task": None,
                    "branch": "integration/tides",
                    "head": "c0ffee1",
                    "into": into,
                    "failed": ["make test", "make lint"],
                }

                # Act
                rendered = COMMAND.render_text(document)

                # Assert
                self.assertEqual(rendered, text)


class RebaseContextRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(pr=42, head=NO_RED_HEAD, into=NO_MAIN_REPAIR)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RebaseContextExitCodeTest(unittest.TestCase):
    def test_should_exit_0(self):
        # Act
        exit_code = COMMAND.decide_exit_code(create_document([]))

        # Assert
        self.assertEqual(exit_code, 0)
