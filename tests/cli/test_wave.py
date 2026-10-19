import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

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
CLOSED = '{"schema_version": 1, "ts": "2026-10-14T10:00:00Z", "event": "wave.closed", "wave": "shop_w1", "pr": 31}\n'
CANCELLED = (
    '{"schema_version": 1, "ts": "2026-10-14T10:00:00Z", "event": "wave.cancelled", "wave": "shop_w1",'
    ' "reason": "user"}\n'
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

    def test_should_print_the_wave_as_text(self):
        # Act
        completed = self.run_wave("show", "shop_w1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "wave shop_w1 of @PROJECT.shop on integration/shop_w1, started 2026-10-13T09:00:00Z,"
            " last event wave.started\n"
            "task  state    pull request  run\n"
            "S3    running  -             20261013T121500Z-a00002\n"
            "S4    pr_open  12            -\n"
            "S5    -        -             -\n",
        )

    def test_should_exit_1_naming_a_wave_no_wave_started_names(self):
        # Act
        completed = self.run_wave("show", "shop_w9")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave show: no wave.started names the wave shop_w9\n"),
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

    def test_should_narrow_the_rows_to_one_project(self):
        # Act
        completed = self.run_wave("list", "--project", "shop", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            [row["wave"] for row in json.loads(completed.stdout)["waves"]], ["shop_w2", "shop_w1", "shop_w3"]
        )

    def test_should_print_the_rows_as_text(self):
        # Act
        completed = self.run_wave("list")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "wave     project  branch               last event      tasks\n"
            "cafe_w1  cafe     integration/cafe_w1  wave.paused     1\n"
            "shop_w2  shop     integration/shop_w2  wave.reported   1\n"
            "shop_w1  shop     integration/shop_w1  wave.closed     2\n"
            "shop_w3  shop     integration/shop_w3  wave.cancelled  2\n",
        )


class BrigadeWaveListOfAnEmptyLedgerTest(WaveTestCase):
    def test_should_print_no_row(self):
        # Act
        completed = self.run_wave("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"schema_version": 1, "waves": []})


class BrigadeWaveCancelTest(WaveTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger(CANCELLED_WAVE_EVENTS)

    def test_should_record_the_cancellation_in_the_ledger(self):
        # Act
        self.run_wave("cancel", "shop_w1")

        # Assert
        lines = (self.ledger / "2026-10.jsonl").read_text().splitlines()
        self.assertEqual(
            json.loads(lines[-1]),
            {"schema_version": 1, "ts": ANY, "event": "wave.cancelled", "wave": "shop_w1", "reason": "user"},
        )

    def test_should_list_what_it_leaves_in_place_as_text(self):
        # Act
        completed = self.run_wave("cancel", "shop_w1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "wave shop_w1 cancelled\n"
            "task  stopped run  worktree  branch           pull request\n"
            "S3    -            -         -                -\n"
            "S4    -            -         task/shop_w1/S4  12\n",
        )

    def test_should_exit_1_naming_the_last_event_of_a_wave_already_ended(self):
        for ending, expected_stderr in [
            (CLOSED, "brigade wave cancel: the wave shop_w1 ended on wave.closed\n"),
            (CANCELLED, "brigade wave cancel: the wave shop_w1 ended on wave.cancelled\n"),
        ]:
            with self.subTest(ending=ending):
                # Arrange
                self.write_ledger(CANCELLED_WAVE_EVENTS + ending)

                # Act
                completed = self.run_wave("cancel", "shop_w1")

                # Assert
                self.assertEqual((completed.returncode, completed.stderr), (1, expected_stderr))

    def test_should_exit_1_naming_a_wave_no_wave_started_names(self):
        # Act
        completed = self.run_wave("cancel", "shop_w9")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave cancel: no wave.started names the wave shop_w9\n"),
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

    def test_should_stop_the_live_run_of_a_task_of_the_wave(self):
        # Act
        self.run_brigade("wave", "cancel", "shop_w1")

        # Assert
        self.assert_process_gone(self.client_pid)
        [listed] = json.loads(self.run_brigade("runs", "list", "--json").stdout)["runs"]
        self.assertEqual((listed["state"], listed["outcome"]), ("finished", "stopped"))

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


class BrigadeWaveCancelOfAWaveWithAFinishedRunTest(RunTestCase):
    def test_should_list_the_worktree_of_the_finished_run_and_stop_nothing(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(CANCELLED_WAVE_EVENTS)
        deliver = ("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace))
        self.run_brigade(*deliver, "--wave", "shop_w1", "--task", "S3")

        # Act
        completed = self.run_brigade("wave", "cancel", "shop_w1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["tasks"][0],
            {
                "task": "S3",
                "stopped_run": None,
                "worktree": str(self.workspace),
                "branch": None,
                "pull_request": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
