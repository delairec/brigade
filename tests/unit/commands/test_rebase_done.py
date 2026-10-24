import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.rebase_done import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner, create_corpus_double, write_ledger
from tests.unit.commands.test_verify_preflight import TASK_PR_OPENED, TIDEPOOL_PROJECT, WAVE_STARTED

DESCENDING = ProcessAnswer()
NOT_DESCENDING = ProcessAnswer(exit_code=1)
PUSH_WITH_A_LEASE_ON_THE_REMOTE_HEAD = (
    "git",
    "push",
    "--quiet",
    "--force-with-lease=task/M4-tides/T7:8885daa",
    "origin",
    "HEAD:task/M4-tides/T7",
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.select_argvs_opening_on import select_argvs_opening_on

GIT_PUSH = ("git", "push")
DONE_DOCUMENT = {
    "schema_version": 1,
    "project": "tidepool",
    "pr": 42,
    "task": "T7",
    "branch": "task/M4-tides/T7",
    "base": "integration/M4-tides",
    "head": "9a9a9a9",
}


class RebaseDoneTextTest(unittest.TestCase):
    def test_should_name_the_branch_pushed_its_head_and_its_base(self):
        # Act
        text = COMMAND.render_text(DONE_DOCUMENT)

        # Assert
        self.assertEqual(text, "task/M4-tides/T7 pushed at 9a9a9a9 on top of integration/M4-tides for #42, @TASK.T7")


class RebaseDoneOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED, TASK_PR_OPENED])

    def _create_runtime(self, ancestry: ProcessAnswer):
        answers = {
            ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout="/home/user/tidepool-T7\n"),
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                stdout="/home/user/tidepool/.git\n"
            ),
            ("git", "fetch"): ProcessAnswer(),
            ("git", "merge-base", "--is-ancestor", "origin/integration/M4-tides", "HEAD"): ancestry,
            ("git", "rev-parse", "--verify"): ProcessAnswer(stdout="8885daa\n"),
            ("git", "rev-parse", "HEAD"): ProcessAnswer(stdout="9a9a9a9\n"),
            ("git", "push"): ProcessAnswer(),
        }
        self.machine = ScriptedProcessRunner(
            answers, fallback=create_corpus_double({"PROJECT": {"tidepool": TIDEPOOL_PROJECT}})
        )
        return create_test_runtime(create_test_paths(self.root), run_process=self.machine.run)

    def test_should_push_a_branch_descending_from_the_head_of_its_base_with_a_lease_on_its_remote_head(self):
        # Arrange
        runtime = self._create_runtime(DESCENDING)

        # Act
        document = COMMAND.run(Namespace(pr=42), runtime)

        # Assert
        self.assertEqual(document["head"], "9a9a9a9")
        self.assertEqual(select_argvs_opening_on(self.machine.argvs, GIT_PUSH), [PUSH_WITH_A_LEASE_ON_THE_REMOTE_HEAD])

    def test_should_refuse_a_branch_that_does_not_descend_from_the_head_of_its_base_and_push_nothing(self):
        # Arrange
        runtime = self._create_runtime(NOT_DESCENDING)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pr=42), runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "task/M4-tides/T7 does not descend from the head of integration/M4-tides: rebase it first",
        )
        self.assertEqual(select_argvs_opening_on(self.machine.argvs, GIT_PUSH), [])


class RebaseDoneRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(pr=42)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RebaseDoneExitCodeTest(unittest.TestCase):
    def test_should_exit_0(self):
        # Act
        exit_code = COMMAND.decide_exit_code(DONE_DOCUMENT)

        # Assert
        self.assertEqual(exit_code, 0)
