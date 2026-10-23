import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.rebase_context import COMMAND
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    create_corpus_double,
    create_runtime,
    write_ledger,
)
from tests.unit.commands.test_verify_preflight import TASK_PR_OPENED, TASK_WORKTREE, TIDEPOOL_PROJECT, WAVE_STARTED

MERGE_TREE = (
    "git",
    "merge-tree",
    "--write-tree",
    "--name-only",
    "--no-messages",
    "HEAD",
    "origin/integration/M4-tides",
)
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
            **{prefix: ProcessAnswer(stdout=stdout) for prefix, stdout in TASK_WORKTREE.items()},
            MERGE_TREE: merge,
        }
        machine = ScriptedProcessRunner(
            answers, fallback=create_corpus_double({"PROJECT": {"tidepool": TIDEPOOL_PROJECT}})
        )
        return create_runtime(self.root, run_process=machine.run)

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
