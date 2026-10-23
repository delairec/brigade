import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.wave_cancel import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.commands.run_directories import FIRST_RUN, create_run_record, create_run_result, write_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

STARTED = {
    "schema_version": 2,
    "ts": "2026-10-13T09:00:00Z",
    "event": "wave.started",
    "wave": "shop_w1",
    "project": "shop",
    "branch": "integration/shop_w1",
    "tasks": ["S3", "S4"],
}
PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-13T11:10:00Z",
    "event": "task.pr_opened",
    "project": "shop",
    "task": "S4",
    "wave": "shop_w1",
    "branch": "task/shop_w1/S4",
    "pr": 12,
    "login": "octo-bot",
}
CLOSED = {"schema_version": 1, "ts": "2026-10-14T10:00:00Z", "event": "wave.closed", "wave": "shop_w1", "pr": 31}
CANCELLED = {
    "schema_version": 1,
    "ts": "2026-10-14T10:00:00Z",
    "event": "wave.cancelled",
    "wave": "shop_w1",
    "reason": "user",
}


class WaveCancelTextTest(unittest.TestCase):
    def test_should_list_what_the_cancellation_leaves_in_place(self):
        # Arrange
        document = {
            "schema_version": 1,
            "wave": "shop_w1",
            "tasks": [
                {"task": "S3", "stopped_run": FIRST_RUN, "worktree": "/srv/s3", "branch": None, "pull_request": None},
                {"task": "S4", "stopped_run": None, "worktree": None, "branch": "task/shop_w1/S4", "pull_request": 12},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "wave shop_w1 cancelled\n"
            "task  stopped run              worktree  branch           pull request\n"
            "S3    20261007T090000Z-b70a01  /srv/s3   -                -\n"
            "S4    -                        -         task/shop_w1/S4  12",
        )


class WaveCancelExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveCancelRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(wave="shop_w1")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveCancelOfAnOpenWaveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(self.root, [STARTED, PR_OPENED])
        write_run(
            self.root / "state",
            create_run_record(FIRST_RUN, "shop_w1", "S3"),
            create_run_result(FIRST_RUN, "done", "2026-10-13T12:00:00Z"),
        )

    def test_should_record_the_cancellation_in_the_ledger(self):
        # Act
        COMMAND.run(Namespace(wave="shop_w1"), create_test_runtime(create_test_paths(self.root)))

        # Assert
        lines = (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            json.loads(lines[-1]),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "wave.cancelled",
                "wave": "shop_w1",
                "reason": "user",
            },
        )

    def test_should_list_the_worktree_of_a_finished_run_the_branch_and_the_pull_request_and_stop_nothing(self):
        # Act
        document = COMMAND.run(Namespace(wave="shop_w1"), create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "wave": "shop_w1",
                "tasks": [
                    {
                        "task": "S3",
                        "stopped_run": None,
                        "worktree": "/home/user/tidepool",
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


class WaveCancelOfAWaveNotOpenTest(unittest.TestCase):
    def test_should_refuse_a_wave_already_ended(self):
        for ending, expected_message in [
            (CLOSED, "the wave shop_w1 ended on wave.closed"),
            (CANCELLED, "the wave shop_w1 ended on wave.cancelled"),
        ]:
            with self.subTest(ending=ending["event"]):
                # Arrange
                root = Path(self.enterContext(tempfile.TemporaryDirectory()))
                write_ledger(root, [STARTED, ending])

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    COMMAND.run(Namespace(wave="shop_w1"), create_test_runtime(create_test_paths(root)))

                # Assert
                self.assertEqual(str(raised.exception), expected_message)

    def test_should_refuse_a_wave_no_wave_started_names(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(root, [STARTED])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="shop_w9"), create_test_runtime(create_test_paths(root)))

        # Assert
        self.assertEqual(str(raised.exception), "no wave.started names the wave shop_w9")


if __name__ == "__main__":
    unittest.main()
