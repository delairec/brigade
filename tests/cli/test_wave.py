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
    '{"schema_version": 3, "ts": "2026-10-13T12:10:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T110000Z-a00001", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "failed",'
    ' "error_class": "rate_limit", "main_turns": 50, "total_turns": null}\n'
    '{"schema_version": 3, "ts": "2026-10-13T12:20:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T121500Z-a00002", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_turns": 30, "total_turns": null}\n'
    '{"schema_version": 3, "ts": "2026-10-13T12:30:00Z", "event": "run.finished", "wave": "cafe_w1", "task": "S3",'
    ' "run": "20261013T122500Z-a00003", "client": "fake", "project": "cafe", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "build-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_turns": 30, "total_turns": null}\n'
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
    '{"schema_version": 1, "ts": "2026-10-13T11:30:00Z", "event": "wave.blocked", "wave": "cafe_w1",'
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


RECORDED_WAVE_EVENTS = (
    '{"schema_version": 2, "ts": "2026-09-30T22:00:00Z", "event": "wave.started", "wave": "tidepool_w16",'
    ' "project": "tidepool", "branch": "integration/M1", "tasks": ["T1"]}\n'
    '{"schema_version": 3, "ts": "2026-09-30T22:10:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-a00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "failed",'
    ' "error_class": "rate_limit", "main_turns": 50, "total_turns": null}\n'
    '{"schema_version": 1, "ts": "2026-09-30T22:15:00Z", "event": "wave.parked", "wave": "tidepool_w16", "reason": "quota"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T00:15:00Z", "event": "wave.resumed", "wave": "tidepool_w16", "reason": "quota"}\n'
    '{"schema_version": 3, "ts": "2026-10-01T00:40:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-a00001", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 2, "outcome": "done",'
    ' "error_class": null, "main_turns": 30, "total_turns": null}\n'
    '{"schema_version": 3, "ts": "2026-10-01T00:50:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP147",'
    ' "run": "20261001T000000Z-a00002", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_turns": null, "total_turns": null}\n'
    '{"schema_version": 3, "ts": "2026-10-01T01:00:00Z", "event": "run.finished", "wave": "tidepool_w16", "task": "TP146",'
    ' "run": "20261001T000000Z-a00003", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-pr-review", "role": "remi", "slot": "review", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_turns": 12, "total_turns": null}\n'
    '{"schema_version": 1, "ts": "2026-10-01T01:30:00Z", "event": "pr.merged", "project": "tidepool", "wave": "tidepool_w16",'
    ' "task": "TP146", "pr": 291, "rounds": 1, "login": "tidepool-cli"}\n'
    '{"schema_version": 1, "ts": "2026-10-01T01:40:00Z", "event": "task.parked", "wave": "tidepool_w16", "task": "TP147",'
    ' "reason": "blocked", "blockers": ["OPEN_QUESTION.Undecided"]}\n'
    '{"schema_version": 3, "ts": "2026-10-01T02:00:00Z", "event": "run.finished", "wave": "tidepool_w17", "task": "TP150",'
    ' "run": "20261001T000000Z-a00004", "client": "claude-code", "project": "tidepool", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_turns": 20, "total_turns": null}\n'
)


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
                "pull_request": None,
                "tasks": [
                    {
                        "task": "S3",
                        "state": "running",
                        "pull_request": None,
                        "run": "20261013T121500Z-a00002",
                        "reason": None,
                    },
                    {"task": "S4", "state": "pr_open", "pull_request": 12, "run": None, "reason": None},
                    {"task": "S5", "state": None, "pull_request": None, "run": None, "reason": None},
                ],
                "merge_command": None,
                "task_merge_commands": [],
            },
        )


class BrigadeWaveShowEventsTest(WaveTestCase):
    def setUp(self):
        super().setUp()
        self.write_ledger(RECORDED_WAVE_EVENTS)

    def test_should_print_the_wave_its_measures_and_its_events_in_the_order_recorded(self):
        # Act
        completed = self.run_wave("show", "tidepool_w16", "--events")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                (
                    "wave tidepool_w16 of @PROJECT.tidepool on integration/M1, started 2026-09-30T22:00:00Z,"
                    " last event wave.resumed, pull request -"
                ),
                "task  state  pull request  run  reason",
                "T1    -      -             -    -",
                "wave tidepool_w16: 2026-09-30T22:00:00Z to 2026-10-01T01:40:00Z, wall time 3h40m",
                "cost: none",
                "tokens: none",
                "tasks:",
                "  TP146  turns 92  duration 0h00m  cost -",
                "  TP147  turns -  duration 0h00m  cost -",
                "pull requests: #291 TP146 rounds 1",
                "turns by slot:",
                "  build",
                "    runs p50 80  p90 80  measured 1  partial 0  unmeasured 1",
                "    segments p50 30  p90 50  measured 2  unmeasured 1",
                "  review",
                "    runs p50 12  p90 12  measured 1  partial 0  unmeasured 0",
                "    segments p50 12  p90 12  measured 1  unmeasured 0",
                "turns by role:",
                "  builder",
                "    runs p50 80  p90 80  measured 1  partial 0  unmeasured 1",
                "    segments p50 30  p90 50  measured 2  unmeasured 1",
                "  remi",
                "    runs p50 12  p90 12  measured 1  partial 0  unmeasured 0",
                "    segments p50 12  p90 12  measured 1  unmeasured 0",
                "halts: 1, 2h00m in all",
                "  2026-09-30T22:15:00Z to 2026-10-01T00:15:00Z  2h00m",
                "handovers: TP146 builder build segment 2",
                "parked: TP147",
                "events:",
                "  2026-09-30T22:00:00Z  wave.started",
                "  2026-09-30T22:10:00Z  run.finished  TP146",
                "  2026-09-30T22:15:00Z  wave.parked",
                "  2026-10-01T00:15:00Z  wave.resumed",
                "  2026-10-01T00:40:00Z  run.finished  TP146",
                "  2026-10-01T00:50:00Z  run.finished  TP147",
                "  2026-10-01T01:00:00Z  run.finished  TP146",
                "  2026-10-01T01:30:00Z  pr.merged  TP146",
                "  2026-10-01T01:40:00Z  task.parked  TP147",
            ],
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
                        "last_event": "wave.blocked",
                        "tasks": 1,
                        "started_at": "2026-10-13T09:30:00Z",
                        "ended_at": None,
                        "ended_by": None,
                        "task_states": [{"task": "C2", "state": None}],
                        "halt": {"reason": "quota", "resume_at": "2026-10-13T16:00:00Z"},
                        "rounds": 0,
                        "cost_usd": None,
                    },
                    {
                        "wave": "shop_w2",
                        "project": "shop",
                        "branch": "integration/shop_w2",
                        "last_event": "wave.reported",
                        "tasks": 1,
                        "started_at": "2026-10-13T11:00:00Z",
                        "ended_at": None,
                        "ended_by": None,
                        "task_states": [{"task": "S5", "state": None}],
                        "halt": None,
                        "rounds": 0,
                        "cost_usd": None,
                    },
                    {
                        "wave": "shop_w1",
                        "project": "shop",
                        "branch": "integration/shop_w1",
                        "last_event": "wave.closed",
                        "tasks": 2,
                        "started_at": "2026-10-13T09:00:00Z",
                        "ended_at": "2026-10-13T10:00:00Z",
                        "ended_by": "wave.closed",
                        "task_states": [{"task": "S3", "state": None}, {"task": "S4", "state": None}],
                        "halt": None,
                        "rounds": 0,
                        "cost_usd": None,
                    },
                    {
                        "wave": "shop_w3",
                        "project": "shop",
                        "branch": "integration/shop_w3",
                        "last_event": "wave.cancelled",
                        "tasks": 2,
                        "started_at": "2026-10-13T12:00:00Z",
                        "ended_at": "2026-10-13T12:30:00Z",
                        "ended_by": "wave.cancelled",
                        "task_states": [{"task": "S6", "state": None}, {"task": "S7", "state": None}],
                        "halt": None,
                        "rounds": 0,
                        "cost_usd": None,
                    },
                ],
            },
        )


class BrigadeWaveCancelOfAWaveWithALiveRunTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT + self.hold_the_client())
        self.record("builder", DONE_RESULT)
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(CANCELLED_WAVE_EVENTS)
        deliver = ("run", "start", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace))
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
