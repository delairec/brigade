from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.wave_tick_test_case import WAVE_BRANCH, LaunchingTickTestCase
from tests.value_matchers import DurationUnderMatcher, PatternMatcher

RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"

S3_PARKED_ON_A_DEAD_RUN = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.parked", "wave": "shop_w1", "task": "S3",'
    ' "reason": "run dead: 20261013T093000Z-a00001", "blockers": []}\n'
)


class BrigadeWaveRequeueOfAParkedTaskTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        (self.state / "ledger" / "2026-10.jsonl").write_text(S3_PARKED_ON_A_DEAD_RUN)

    def test_should_queue_the_parked_task_again_for_the_next_tick_to_launch_it(self):
        # Act
        requeued = self.requeue_then_tick()

        # Assert
        self.assertEqual(requeued.returncode, 0, requeued.stderr)
        self.assertEqual(requeued.stdout, "task S3 of shop_w1 queued\n", requeued.stderr)
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-13T09:00:00Z",
                    "event": "wave.started",
                    "wave": "shop_w1",
                    "project": "shop",
                    "branch": "integration/M1-empty-cart",
                    "tasks": ["S3"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:00:00Z",
                    "event": "task.parked",
                    "wave": "shop_w1",
                    "task": "S3",
                    "reason": "run dead: 20261013T093000Z-a00001",
                    "blockers": [],
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "queued",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "running",
                },
                {
                    "schema_version": 2,
                    "ts": ANY,
                    "event": "run.finished",
                    "run": PatternMatcher(RUN_ID_PATTERN),
                    "segment": 1,
                    "procedure": "build-task",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": "shop",
                    "session": "fake-session",
                    "main_steps": 12,
                    "total_steps": None,
                    "duration_ms": DurationUnderMatcher(10000),
                    "usage": {
                        "input_tokens": 120,
                        "output_tokens": 3400,
                        "cache_creation_input_tokens": 16778,
                        "cache_read_input_tokens": 98000,
                    },
                    "outcome": "done",
                    "error_class": None,
                    "exit": 0,
                    "wave": "shop_w1",
                    "task": "S3",
                    "nulls": {"total_steps": "the client reads no transcript", "error_class": "the run did not fail"},
                    "cost_usd": 0.42,
                },
            ],
        )

    def requeue_then_tick(self):
        requeued = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )
        self.run_tick("--once")
        self.wait_for_the_runs()
        return requeued
