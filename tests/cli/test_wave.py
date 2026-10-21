import json
import tempfile
import unittest
from pathlib import Path

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, RunTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

SHOWN_WAVE_EVENTS = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "integration/shop_w1", "tasks": ["S3", "S4", "S5"]}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "queued"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "running"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:10:00Z", "event": "task.state", "wave": "shop_w1", "task": "S4",'
    ' "state": "pr_open"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:10:00Z", "event": "task.pr_opened", "project": "shop",'
    ' "task": "S4", "wave": "shop_w1", "branch": "task/shop_w1/S4", "pr": 12, "login": "octo-bot"}\n'
    '{"schema_version": 2, "ts": "2026-10-13T11:30:00Z", "event": "wave.started", "wave": "cafe_w1",'
    ' "project": "cafe", "branch": "integration/cafe_w1", "tasks": ["S3"]}\n'
    '{"schema_version": 1, "ts": "2026-10-13T12:00:00Z", "event": "task.state", "wave": "cafe_w1", "task": "S3",'
    ' "state": "merged"}\n'
    '{"schema_version": 2, "ts": "2026-10-13T12:10:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T110000Z-a00001", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "failed",'
    ' "error_class": "rate_limit", "main_steps": 50, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-13T12:20:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T121500Z-a00002", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 30, "total_steps": null}\n'
    '{"schema_version": 2, "ts": "2026-10-13T12:30:00Z", "event": "run.finished", "wave": "cafe_w1", "task": "S3",'
    ' "run": "20261013T122500Z-a00003", "client": "fake", "project": "cafe", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 30, "total_steps": null}\n'
)
LISTED_WAVE_EVENTS = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "integration/shop_w1", "tasks": ["S3", "S4"]}\n'
    '{"schema_version": 2, "ts": "2026-10-13T09:30:00Z", "event": "wave.started", "wave": "cafe_w1",'
    ' "project": "cafe", "branch": "integration/cafe_w1", "tasks": ["C2"]}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "wave.closed", "wave": "shop_w1", "pr": 31}\n'
    '{"schema_version": 2, "ts": "2026-10-13T11:00:00Z", "event": "wave.started", "wave": "shop_w2",'
    ' "project": "shop", "branch": "integration/shop_w2", "tasks": ["S5"]}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:20:00Z", "event": "wave.reported", "wave": "shop_w2",'
    ' "run": "20261013T112000Z-a00004"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:30:00Z", "event": "wave.paused", "wave": "cafe_w1",'
    ' "reason": "quota", "resume_at": "2026-10-13T16:00:00Z"}\n'
    '{"schema_version": 2, "ts": "2026-10-13T12:00:00Z", "event": "wave.started", "wave": "shop_w3",'
    ' "project": "shop", "branch": "integration/shop_w3", "tasks": ["S6", "S7"]}\n'
    '{"schema_version": 1, "ts": "2026-10-13T12:30:00Z", "event": "wave.cancelled", "wave": "shop_w3",'
    ' "reason": "user"}\n'
)
CANCELLED_WAVE_EVENTS = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "integration/shop_w1", "tasks": ["S3", "S4"]}\n'
    '{"schema_version": 1, "ts": "2026-10-13T11:10:00Z", "event": "task.pr_opened", "project": "shop",'
    ' "task": "S4", "wave": "shop_w1", "branch": "task/shop_w1/S4", "pr": 12, "login": "octo-bot"}\n'
)
CLIENT_OUTLIVING_THE_TEST = 'delay = "120"\n'


class WaveTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.ledger = self.machine.state_home / "brigade" / "ledger"
        self.ledger.mkdir(parents=True)

    def tearDown(self):
        self.root.cleanup()

    def write_ledger(self, events: str) -> None:
        (self.ledger / "2026-10.jsonl").write_text(events)

    def run_wave(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "wave", *arguments)


class BrigadeWaveShowTest(WaveTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger(SHOWN_WAVE_EVENTS)

    def test_should_print_the_wave_and_each_task_with_its_state_its_pull_request_and_its_run(self):
        # Act
        completed = self.run_wave("show", "shop_w1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "wave": "shop_w1",
                "project": "shop",
                "branch": "integration/shop_w1",
                "started_at": "2026-10-13T09:00:00Z",
                "last_event": "wave.started",
                "tasks": [
                    {"task": "S3", "state": "running", "pull_request": None, "run": "20261013T121500Z-a00002"},
                    {"task": "S4", "state": "pr_open", "pull_request": 12, "run": None},
                    {"task": "S5", "state": None, "pull_request": None, "run": None},
                ],
            },
        )


class BrigadeWaveListTest(WaveTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger(LISTED_WAVE_EVENTS)

    def test_should_print_one_row_per_wave_the_open_waves_first(self):
        # Act
        completed = self.run_wave("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "waves": [
                    {
                        "wave": "cafe_w1",
                        "project": "cafe",
                        "branch": "integration/cafe_w1",
                        "last_event": "wave.paused",
                        "tasks": 1,
                    },
                    {
                        "wave": "shop_w2",
                        "project": "shop",
                        "branch": "integration/shop_w2",
                        "last_event": "wave.reported",
                        "tasks": 1,
                    },
                    {
                        "wave": "shop_w1",
                        "project": "shop",
                        "branch": "integration/shop_w1",
                        "last_event": "wave.closed",
                        "tasks": 2,
                    },
                    {
                        "wave": "shop_w3",
                        "project": "shop",
                        "branch": "integration/shop_w3",
                        "last_event": "wave.cancelled",
                        "tasks": 2,
                    },
                ],
            },
        )


class BrigadeWaveCancelOfAWaveWithALiveRunTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT + CLIENT_OUTLIVING_THE_TEST)
        self.record("builder", DONE_RESULT)
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(CANCELLED_WAVE_EVENTS)
        deliver = ("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace))
        self.run_id = self.run_brigade(*deliver, "--wave", "shop_w1", "--task", "S3", "--detach").stdout.strip()
        self.client_pid = self.wait_for_client(self.read_run_pid(self.run_id))

    def test_should_list_the_stopped_run_its_worktree_the_branch_and_the_pull_request(self):
        # Act
        completed = self.run_brigade("wave", "cancel", "shop_w1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "wave": "shop_w1",
                "tasks": [
                    {
                        "task": "S3",
                        "stopped_run": self.run_id,
                        "worktree": str(self.workspace),
                        "branch": None,
                        "pull_request": None,
                    },
                    {
                        "task": "S4",
                        "stopped_run": None,
                        "worktree": None,
                        "branch": "task/shop_w1/S4",
                        "pull_request": 12,
                    },
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
