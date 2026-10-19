import functools
import itertools
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from brigade.errors import BrigadeError
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.stop_run import stop_run
from brigade.system.stop_signal_receiver import StopSignalReceiver
from tests.process_launcher import ProcessLauncher

RUN_ID = "20261012T090000Z-b136a1"
RUN_RECORD = {
    "schema_version": 1,
    "run": RUN_ID,
    "procedure": "deliver",
    "procedure_path": "built-in",
    "slot": "build",
    "role": "builder",
    "role_source": "built-in",
    "client": "fake",
    "project": None,
    "cwd": "/home/user/tidepool",
    "worktree": "/home/user/tidepool",
    "capabilities": ["read"],
    "budget": 40,
    "wall_limit_s": 1500.0,
    "arguments": {},
    "wave": None,
    "task": None,
    "brief": None,
}
RUN_RESULT = {
    "schema_version": 2,
    "ts": "2026-10-12T09:12:00Z",
    "event": "run.finished",
    "run": RUN_ID,
    "segment": 1,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "client": "fake",
    "project": None,
    "session": "session-b192",
    "main_steps": 12,
    "total_steps": 12,
    "duration_ms": 4200,
    "usage": None,
    "outcome": "stopped",
    "error_class": None,
    "exit": 21,
    "wave": None,
    "task": None,
    "nulls": {},
}
RUN_PROCESS = """
import signal
import sys
from pathlib import Path


def end_the_run(_received, _frame):
    Path(sys.argv[1]).write_text(sys.argv[2], encoding="utf-8")
    sys.exit(0)


signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1})
print("started", flush=True)
signal.sigwait({signal.SIGUSR1})
signal.signal(signal.SIGTERM, end_the_run)
print("ready", flush=True)
while True:
    signal.pause()
"""


def signal_readiness(process: subprocess.Popen) -> None:
    os.kill(process.pid, signal.SIGUSR1)
    process.stdout.readline()


def pause_through(actions):
    return lambda _poll_s: next(actions)()


def _pass() -> None:
    pass


class StopRunTestCase(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.state_root = root / "brigade"
        self.run_directory = self.state_root / "runs" / RUN_ID
        self.run_directory.mkdir(parents=True)
        (self.run_directory / "run.json").write_text(json.dumps(RUN_RECORD))

    def start_run_process(self, result_on_stop: dict) -> subprocess.Popen:
        process = ProcessLauncher.start(
            [sys.executable, "-c", RUN_PROCESS, str(self.run_directory / "result.json"), json.dumps(result_on_stop)],
            stdout=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        process.stdout.readline()
        return process

    def start_gone_process(self) -> int:
        gone = ProcessLauncher.start(["true"])
        record_run_pid(self.run_directory, gone.pid)
        gone.wait()
        return gone.pid


class StopRunOfARunNotYetReadyTest(StopRunTestCase):
    def test_should_signal_its_process_only_once_it_signalled_it_is_ready(self):
        # Arrange
        process = self.start_run_process(RUN_RESULT)
        record_run_pid(self.run_directory, process.pid)
        actions = itertools.chain([functools.partial(signal_readiness, process)], itertools.repeat(process.poll))
        calls = mock.Mock()
        calls.attach_mock(
            self.enterContext(mock.patch.object(time, "sleep", side_effect=pause_through(actions))), "pause"
        )
        calls.attach_mock(self.enterContext(mock.patch.object(os, "kill", wraps=os.kill)), "kill")

        # Act
        ended = stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual(
            calls.mock_calls[:3],
            [
                mock.call.pause(0.1),
                mock.call.kill(process.pid, signal.SIGUSR1),
                mock.call.kill(process.pid, signal.SIGTERM),
            ],
        )
        self.assertEqual((ended["state"], ended["outcome"]), ("finished", "stopped"))


class StopRunOfARunWhosePidFileStillNamesTheProcessThatLaunchedItTest(StopRunTestCase):
    def test_should_signal_the_ready_process_that_replaced_it_in_the_pid_file(self):
        # Arrange
        self.start_gone_process()
        process = self.start_run_process(RUN_RESULT)
        signal_readiness(process)
        actions = itertools.chain(
            [functools.partial(record_run_pid, self.run_directory, process.pid)], itertools.repeat(process.poll)
        )
        self.enterContext(mock.patch.object(time, "sleep", side_effect=pause_through(actions)))

        # Act
        ended = stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual((ended["state"], ended["outcome"]), ("finished", "stopped"))


class StopRunOfARunNeverReadyTest(StopRunTestCase):
    def test_should_refuse_the_run_naming_the_bound_and_send_no_signal(self):
        # Arrange
        process = self.start_run_process(RUN_RESULT)
        record_run_pid(self.run_directory, process.pid)
        self.enterContext(mock.patch.object(time, "sleep", side_effect=pause_through(itertools.repeat(process.poll))))
        kill = self.enterContext(mock.patch.object(os, "kill", wraps=os.kill))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual(
            (str(refusal.exception), kill.mock_calls),
            (f"run {RUN_ID} has not signalled it is ready within 10 s: no signal sent", []),
        )


class StopRunOfARunWhoseProcessIsGoneTest(StopRunTestCase):
    def test_should_refuse_the_run_as_dead_naming_its_pid(self):
        # Arrange
        gone_pid = self.start_gone_process()
        self.enterContext(mock.patch.object(time, "sleep", side_effect=pause_through(itertools.repeat(_pass))))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual(
            str(refusal.exception), f"run {RUN_ID} is dead: no process of its identity holds its pid {gone_pid}"
        )


class StopRunOfARunThatEndsOtherwiseThanStoppedTest(StopRunTestCase):
    def test_should_refuse_the_run_naming_the_state_it_ended_in(self):
        # Arrange
        process = self.start_run_process({**RUN_RESULT, "outcome": "done", "exit": 0})
        signal_readiness(process)
        record_run_pid(self.run_directory, process.pid)
        self.enterContext(mock.patch.object(time, "sleep", side_effect=pause_through(itertools.repeat(process.poll))))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), f"run {RUN_ID} ended finished, not stopped")


class StopRunOfARunAlreadyFinishedTest(StopRunTestCase):
    def test_should_refuse_the_run_naming_its_outcome(self):
        # Arrange
        (self.run_directory / "result.json").write_text(json.dumps({**RUN_RESULT, "outcome": "done", "exit": 0}))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), f"run {RUN_ID} has already finished on done")


class StopRunOfARunHoldingNoPidFileTest(StopRunTestCase):
    def test_should_refuse_the_run_naming_the_missing_pid_file(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), f"run {RUN_ID} holds no pid file naming its process")


class StopRunOfAProcessReapedBeforeItsSignalTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "brigade"
        run_directory = self.state_root / "runs" / RUN_ID
        run_directory.mkdir(parents=True)
        (run_directory / "run.json").write_text(json.dumps(RUN_RECORD))
        self.living_pid = os.getpid()
        record_run_pid(run_directory, self.living_pid)

    def tearDown(self):
        self.root.cleanup()

    def test_should_refuse_the_run_as_dead_naming_its_pid(self):
        # Arrange
        reaped_before_its_signal = ProcessLookupError(3, "No such process")
        self.enterContext(StopSignalReceiver())

        # Act
        with (
            mock.patch.object(os, "kill", side_effect=reaped_before_its_signal),
            self.assertRaises(BrigadeError) as refusal,
        ):
            stop_run(self.state_root, RUN_ID)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"run {RUN_ID} is dead: no process of its identity holds its pid {self.living_pid}",
        )
