import itertools
import shutil
import signal
import tempfile
import unittest
from collections.abc import Iterable, Iterator
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.stop_run import ProcessSignaller, stop_run
from tests.unit.runs.write_run_record import write_run_record
from tests.unit.runs.write_run_result import write_run_result

RUN_ID = "20261019T090000Z-c0ffee"
RUN_PID = 4242
RUN_IDENTITY = "1234567 3f1c-boot"
LAUNCHER_PID = 4241
LAUNCHER_IDENTITY = "1234500 3f1c-boot"
WAITS_UNTIL_THE_READINESS_BOUND = [("wait", 0.1)] * 100


def write_pid_file(run_directory: Path, pid: int, identity: str) -> None:
    (run_directory / "pid").write_text(f"{pid} {identity}\n")


class RunProcessDouble:
    def __init__(
        self,
        result: Path,
        identities: dict[int, Iterator[str | None]],
        catching: Iterable[bool] = (True,),
        outcome_on_signal: str | None = None,
    ):
        self.result = result
        self.identities = identities
        self.catching = iter(catching)
        self.outcome_on_signal = outcome_on_signal
        self.calls = []

    def signal_process(self, pid: int, signal_number: int) -> None:
        self.calls.append(("signal", pid, signal_number))
        if self.outcome_on_signal is None:
            raise ProcessLookupError(3, "No such process")
        write_run_result(self.result, self.outcome_on_signal)

    def read_identity(self, pid: int) -> str | None:
        return next(self.identities[pid])

    def is_catching_signal(self, pid: int, caught: int) -> bool:
        return {(RUN_PID, signal.SIGTERM): next(self.catching)}[(pid, caught)]

    def wait(self, seconds: float) -> None:
        self.calls.append(("wait", seconds))

    def create_signaller(self) -> ProcessSignaller:
        return ProcessSignaller(
            signal_process=self.signal_process,
            read_identity=self.read_identity,
            is_catching_signal=self.is_catching_signal,
            wait=self.wait,
        )


class LaunchedRunProcessDouble(RunProcessDouble):
    def __init__(self, result: Path, identities: dict[int, Iterator[str | None]], outcome_on_signal: str):
        super().__init__(result, identities, outcome_on_signal=outcome_on_signal)

    def wait(self, seconds: float) -> None:
        super().wait(seconds)
        write_pid_file(self.result.parent, RUN_PID, RUN_IDENTITY)


class StopRunTestCase(unittest.TestCase):
    def setUp(self):
        self.state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.state_root)
        self.run_directory = self.state_root / "runs" / RUN_ID
        write_run_record(self.run_directory)
        self.result = self.run_directory / "result.json"


class StopRunOfARunningRunTest(StopRunTestCase):
    def test_should_signal_its_process_wait_for_it_to_end_and_answer_the_stopped_run(self):
        # Arrange
        write_pid_file(self.run_directory, RUN_PID, RUN_IDENTITY)
        process = RunProcessDouble(
            self.result, {RUN_PID: iter([RUN_IDENTITY, RUN_IDENTITY, None])}, outcome_on_signal="stopped"
        )

        # Act
        ended = stop_run(self.state_root, RUN_ID, process.create_signaller())

        # Assert
        self.assertEqual(
            ((ended["state"], ended["outcome"]), process.calls),
            (("finished", "stopped"), [("signal", RUN_PID, signal.SIGTERM), ("wait", 0.1)]),
        )


class StopRunOfARunNotYetReadyTest(StopRunTestCase):
    def test_should_signal_its_process_only_once_it_signalled_it_is_ready(self):
        # Arrange
        write_pid_file(self.run_directory, RUN_PID, RUN_IDENTITY)
        process = RunProcessDouble(
            self.result,
            {RUN_PID: iter([RUN_IDENTITY, RUN_IDENTITY, None])},
            catching=(False, True),
            outcome_on_signal="stopped",
        )

        # Act
        stop_run(self.state_root, RUN_ID, process.create_signaller())

        # Assert
        self.assertEqual(process.calls, [("wait", 0.1), ("signal", RUN_PID, signal.SIGTERM)])


class StopRunOfARunWhosePidFileStillNamesTheProcessThatLaunchedItTest(StopRunTestCase):
    def test_should_signal_the_ready_process_that_replaced_it_in_the_pid_file(self):
        # Arrange
        write_pid_file(self.run_directory, LAUNCHER_PID, LAUNCHER_IDENTITY)
        process = LaunchedRunProcessDouble(
            self.result, {LAUNCHER_PID: iter([None]), RUN_PID: iter([RUN_IDENTITY, None])}, outcome_on_signal="stopped"
        )

        # Act
        ended = stop_run(self.state_root, RUN_ID, process.create_signaller())

        # Assert
        self.assertEqual(
            ((ended["state"], ended["outcome"]), process.calls),
            (("finished", "stopped"), [("wait", 0.1), ("signal", RUN_PID, signal.SIGTERM)]),
        )


class StopRunOfARunNeverReadyTest(StopRunTestCase):
    def test_should_refuse_the_run_naming_the_bound_and_send_no_signal(self):
        # Arrange
        write_pid_file(self.run_directory, RUN_PID, RUN_IDENTITY)
        process = RunProcessDouble(
            self.result, {RUN_PID: itertools.repeat(RUN_IDENTITY)}, catching=itertools.repeat(object=False)
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID, process.create_signaller())

        # Assert
        self.assertEqual(
            (str(refusal.exception), process.calls),
            (
                f"run {RUN_ID} has not signalled it is ready within 10 s: no signal sent",
                WAITS_UNTIL_THE_READINESS_BOUND,
            ),
        )


class StopRunOfARunWhoseProcessIsGoneTest(StopRunTestCase):
    def test_should_refuse_the_run_as_dead_naming_its_pid(self):
        for case, identity in [("held by another process", "7654321 3f1c-boot"), ("reaped", None)]:
            with self.subTest(case=case):
                # Arrange
                write_pid_file(self.run_directory, RUN_PID, RUN_IDENTITY)
                process = RunProcessDouble(self.result, {RUN_PID: itertools.repeat(identity)})

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    stop_run(self.state_root, RUN_ID, process.create_signaller())

                # Assert
                self.assertEqual(
                    (str(refusal.exception), process.calls),
                    (f"run {RUN_ID} is dead: no process of its identity holds its pid {RUN_PID}", [("wait", 0.1)]),
                )


class StopRunOfARunThatEndsOtherwiseThanStoppedTest(StopRunTestCase):
    def test_should_refuse_the_run_naming_the_state_it_ended_in(self):
        # Arrange
        write_pid_file(self.run_directory, RUN_PID, RUN_IDENTITY)
        process = RunProcessDouble(self.result, {RUN_PID: iter([RUN_IDENTITY, None])}, outcome_on_signal="done")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID, process.create_signaller())

        # Assert
        self.assertEqual(str(refusal.exception), f"run {RUN_ID} ended finished, not stopped")


class StopRunOfARunAlreadyFinishedTest(StopRunTestCase):
    def test_should_refuse_the_run_naming_its_outcome(self):
        # Arrange
        write_run_result(self.result, "done")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID, RunProcessDouble(self.result, {}).create_signaller())

        # Assert
        self.assertEqual(str(refusal.exception), f"run {RUN_ID} has already finished on done")


class StopRunOfARunHoldingNoPidFileTest(StopRunTestCase):
    def test_should_refuse_the_run_naming_the_missing_pid_file(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID, RunProcessDouble(self.result, {}).create_signaller())

        # Assert
        self.assertEqual(str(refusal.exception), f"run {RUN_ID} holds no pid file naming its process")


class StopRunOfAProcessReapedBeforeItsSignalTest(StopRunTestCase):
    def test_should_refuse_the_run_as_dead_naming_its_pid(self):
        # Arrange
        write_pid_file(self.run_directory, RUN_PID, RUN_IDENTITY)
        reaped_before_its_signal = RunProcessDouble(self.result, {RUN_PID: iter([RUN_IDENTITY])})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID, reaped_before_its_signal.create_signaller())

        # Assert
        self.assertEqual(
            str(refusal.exception), f"run {RUN_ID} is dead: no process of its identity holds its pid {RUN_PID}"
        )
