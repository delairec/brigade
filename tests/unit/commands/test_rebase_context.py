import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.rebase_context import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner, create_corpus_double, write_ledger
from tests.unit.commands.test_verify_preflight import TASK_PR_OPENED, TIDEPOOL_PROJECT, WAVE_STARTED

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

CONFLICTING_MERGE = ProcessAnswer(stdout="4b825dc\nsrc/tides.py\nREADME.md\n", exit_code=1)
CLEAN_MERGE = ProcessAnswer(stdout="4b825dc\n")


def create_document(conflicts: list[str]) -> dict:
    return {
        "schema_version": 1,
        "project": "tidepool",
        "pr": 42,
        "task": "T7",
        "branch": "task/M4-tides/T7",
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
            text, "# branch\ntask/M4-tides/T7\n\n# base\nintegration/M4-tides\n\n# conflicts\nsrc/tides.py\nREADME.md"
        )


class RebaseContextOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED, TASK_PR_OPENED])

    def _create_runtime(self, merge: ProcessAnswer):
        answers = {
            ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout="/home/user/tidepool-T7\n"),
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                stdout="/home/user/tidepool/.git\n"
            ),
            MERGE_TREE: merge,
        }
        machine = ScriptedProcessRunner(
            answers, fallback=create_corpus_double({"PROJECT": {"tidepool": TIDEPOOL_PROJECT}})
        )
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
                document = COMMAND.run(Namespace(pr=42), runtime)

                # Assert
                self.assertEqual(document, create_document(conflicts))


WITHOUT_FORGE = (("PATH", "/srv/tidepool"),)
ON_GITHUB = (("PATH", "/srv/tidepool"), ("FORGE", "github"))
NO_PULL_REQUEST = None


class RebaseContextOfATaskWithoutAPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED])

    def _create_runtime(self, project: tuple, base: str):
        answers = {
            ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout="/srv/tidepool-T7\n"),
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                stdout="/srv/tidepool/.git\n"
            ),
            ("git", "branch", "--show-current"): ProcessAnswer(stdout="task/M4-tides/T7\n"),
            ("git", "fetch", "--quiet", "origin", "integration/M4-tides"): ProcessAnswer(),
            (*MERGE_TREE[:-1], base): CONFLICTING_MERGE,
        }
        machine = ScriptedProcessRunner(answers, fallback=create_corpus_double({"PROJECT": {"tidepool": project}}))
        return create_test_runtime(create_test_paths(self.root), run_process=machine.run)

    def test_should_read_the_task_from_the_branch_of_the_worktree_and_its_conflicts_with_the_wave_branch(self):
        for case, project, base in [
            ("a project without a forge", WITHOUT_FORGE, "integration/M4-tides"),
            ("a project on GitHub", ON_GITHUB, "origin/integration/M4-tides"),
        ]:
            with self.subTest(case=case):
                # Arrange
                runtime = self._create_runtime(project, base)

                # Act
                document = COMMAND.run(Namespace(pr=NO_PULL_REQUEST), runtime)

                # Assert
                self.assertEqual(
                    document,
                    {
                        "schema_version": 1,
                        "project": "tidepool",
                        "pr": None,
                        "task": "T7",
                        "branch": "task/M4-tides/T7",
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


class RebaseContextOfAMilestoneOrWaveBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [TIDES_BRANCH_CUT, WAVE_STARTED])

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
                "a wave branch without a forge",
                MILESTONE_WITHOUT_FORGE,
                "integration/M4-tides",
                "integration/tides",
                "integration/tides",
            ),
            (
                "a wave branch on GitHub",
                MILESTONE_ON_GITHUB,
                "integration/M4-tides",
                "integration/tides",
                "origin/integration/tides",
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                runtime = self._create_runtime(project, branch, upstream)

                # Act
                document = COMMAND.run(Namespace(pr=NO_PULL_REQUEST), runtime)

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
            COMMAND.run(Namespace(pr=NO_PULL_REQUEST), runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "the branch feature/tides is not a task, a wave or a milestone branch of @PROJECT.tidepool",
        )


class RebaseContextRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(pr=42)

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
