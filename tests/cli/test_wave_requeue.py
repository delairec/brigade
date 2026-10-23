from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_tick import WAVE_BRANCH, LaunchingTickTestCase

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
        self.assertEqual((requeued.returncode, requeued.stdout), (0, "task S3 of shop_w1 queued\n"), requeued.stderr)
        self.assertEqual(
            self.read_events("task.state"),
            [
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
            ],
        )

    def requeue_then_tick(self):
        requeued = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )
        self.run_tick("--once")
        return requeued
