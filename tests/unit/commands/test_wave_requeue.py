import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.wave_requeue import COMMAND
from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.runtime import Runtime
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    create_corpus_double,
    create_machine_double,
    write_ledger,
    write_operational_corpus,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-10-19T08:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "tasks": ["T7", "T8"],
}
PARKED_ON_A_DEAD_RUN = {
    "schema_version": 1,
    "ts": "2026-10-19T08:30:00Z",
    "event": "task.parked",
    "wave": "tidepool_w16",
    "task": "T7",
    "reason": "run dead: 20261019T080500Z-a1b2c3",
    "blockers": [],
}
PARKED_ON_A_FAILED_SETUP = {
    "schema_version": 1,
    "ts": "2026-10-19T08:30:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "parked",
    "reason": "setup failed",
}
WAVE_HEAD = "8885daa"
MAIN_HEAD = "5c2e854"
TIDEPOOL_WITHOUT_FORGE = (("PATH", "/srv/tidepool"), ("MAIN", "main"))
TIDEPOOL_ON_GITHUB = (("PATH", "/srv/tidepool"), ("MAIN", "main"), ("FORGE", "github"))
GITHUB_FORGE = object()
T7_RULED_ON_MAIN = ProcessAnswer(stdout='{"fields": [{"name": "STATUS", "atoms": ["\\"draft\\""]}]}')
T7_ABSENT_FROM_MAIN = ProcessAnswer(exit_code=1, stderr="@TASK.T7 is not defined in the workspace")
IMPLEMENTED_TASKS_QUERY = ("awawa", "status", "TASK", "--where", "STATUS==implemented")
NO_TASK_IMPLEMENTED = '{"entities": []}'
T7_IMPLEMENTED = '{"entities": [{"type": "TASK", "name": "T7"}]}'
RUNNING = {
    "schema_version": 1,
    "ts": "2026-10-19T08:30:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "running",
}


class WaveRequeueTextTest(unittest.TestCase):
    def test_should_name_the_task_queued_again(self):
        # Arrange
        document = {"schema_version": 1, "wave": "tidepool_w16", "task": "T7", "state": "queued"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "task T7 of tidepool_w16 queued")


class WaveRequeueExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code(
            {"schema_version": 1, "wave": "tidepool_w16", "task": "T7", "state": "queued"}
        )

        # Assert
        self.assertEqual(exit_code, 0)


class WaveRequeueRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(wave="tidepool_w16", task="T7")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


def create_wave_tree_runtime(root: Path, implemented_tasks: str) -> Runtime:
    write_operational_corpus(root)
    (root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
    corpus = {
        "PROJECT": {"tidepool": (("PATH", "/srv/tidepool"), ("MAIN", "main"))},
        "TASK": {"T7": (("STATUS", "todo"),)},
    }
    outputs = {("git", "rev-parse", "--verify"): f"{WAVE_HEAD}\n", IMPLEMENTED_TASKS_QUERY: implemented_tasks}
    return create_test_runtime(create_test_paths(root), run_process=create_machine_double(corpus, outputs))


def create_main_tree_runtime(
    root: Path, task_on_main: ProcessAnswer, project: tuple = TIDEPOOL_WITHOUT_FORGE, main: str = "main"
) -> Runtime:
    write_operational_corpus(root)
    (root / "cache" / "refs" / "tidepool" / WAVE_HEAD).mkdir(parents=True)
    (root / "cache" / "refs" / "tidepool" / MAIN_HEAD).mkdir(parents=True)
    corpus = {"PROJECT": {"tidepool": project}, "TASK": {"T7": (("STATUS", "todo"),)}}
    main_root = str(root / "cache" / "refs" / "tidepool" / MAIN_HEAD)
    answers = {
        ("git", "rev-parse", "--verify"): ProcessAnswer(stdout=f"{WAVE_HEAD}\n"),
        ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{main}^{{commit}}"): ProcessAnswer(
            stdout=f"{MAIN_HEAD}\n"
        ),
        ("git", "fetch", "--quiet", "origin", "main"): ProcessAnswer(),
        IMPLEMENTED_TASKS_QUERY: ProcessAnswer(stdout=NO_TASK_IMPLEMENTED),
        ("awawa", "show", "@TASK.T7", "--json", main_root): task_on_main,
    }
    runner = ScriptedProcessRunner(answers, fallback=create_corpus_double(corpus))
    return create_test_runtime(
        create_test_paths(root), run_process=runner.run, resolve_plugin=lambda kind, name: GITHUB_FORGE
    )


class WaveRequeueOfAParkedTaskTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_wave_tree_runtime(self.root, NO_TASK_IMPLEMENTED)

    def test_should_record_the_parked_task_queued(self):
        for case, parking in [
            ("parked by task.parked", PARKED_ON_A_DEAD_RUN),
            ("parked by task.state", PARKED_ON_A_FAILED_SETUP),
        ]:
            with self.subTest(case=case):
                # Arrange
                write_ledger(self.root, [WAVE_STARTED, parking])

                # Act
                COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), self.runtime)

                # Assert
                self.assertEqual(
                    read_ledger(self.runtime.paths.state_root).entries[-1].event,
                    TaskState(wave="tidepool_w16", task="T7", state="queued"),
                )

    def test_should_describe_the_task_queued_again(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "wave": "tidepool_w16", "task": "T7", "state": "queued"})


class WaveRequeueOfAParkedTaskTheMainBranchDoesNotHoldTest(unittest.TestCase):
    def test_should_record_the_parked_task_queued(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        runtime = create_main_tree_runtime(root, T7_ABSENT_FROM_MAIN)
        write_ledger(root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

        # Act
        COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), runtime)

        # Assert
        self.assertEqual(
            read_ledger(runtime.paths.state_root).entries[-1].event,
            TaskState(wave="tidepool_w16", task="T7", state="queued"),
        )


class WaveRequeueRefusalTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_test_runtime(create_test_paths(self.root))

    def test_should_refuse_a_task_that_is_not_parked_naming_its_state(self):
        for case, events, expected_refusal in [
            ("running", [WAVE_STARTED, RUNNING], "the task T7 of the wave tidepool_w16 is running, not parked"),
            ("with no state yet", [WAVE_STARTED], "the task T7 of the wave tidepool_w16 is queued, not parked"),
        ]:
            with self.subTest(case=case):
                # Arrange
                write_ledger(self.root, events)

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), self.runtime)

                # Assert
                self.assertEqual(str(raised.exception), expected_refusal)

    def test_should_refuse_a_parked_task_the_wave_tree_holds_implemented_naming_the_wave_branch(self):
        # Arrange
        runtime = create_wave_tree_runtime(self.root, T7_IMPLEMENTED)
        write_ledger(self.root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "the task T7 of the wave tidepool_w16 is already implemented on integration/tidepool_w16",
        )

    def test_should_refuse_a_task_outside_the_wave_naming_the_wave(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w16", task="T9"), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the task T9 is not a task of the wave tidepool_w16")

    def test_should_refuse_a_wave_no_wave_started_names(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w99", task="T7"), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no wave.started names the wave tidepool_w99")

    def test_should_refuse_a_parked_task_ruled_on_main_naming_the_two_branches_and_the_cancellation(self):
        for case, project, main, expected_refusal in [
            (
                "a project without a forge",
                TIDEPOOL_WITHOUT_FORGE,
                "main",
                (
                    "the task T7 of the wave tidepool_w16 differs between main and integration/tidepool_w16:"
                    " the ruling on main reaches it through brigade wave cancel tidepool_w16 and a new wave cut from main"
                ),
            ),
            (
                "a project on GitHub",
                TIDEPOOL_ON_GITHUB,
                "origin/main",
                (
                    "the task T7 of the wave tidepool_w16 differs between origin/main and integration/tidepool_w16:"
                    " the ruling on main reaches it through brigade wave cancel tidepool_w16"
                    " and a new wave cut from origin/main"
                ),
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                root = Path(self.enterContext(tempfile.TemporaryDirectory()))
                runtime = create_main_tree_runtime(root, T7_RULED_ON_MAIN, project, main)
                write_ledger(root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), runtime)

                # Assert
                self.assertEqual(str(raised.exception), expected_refusal)
