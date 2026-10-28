import json
from unittest.mock import ANY

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, RunTestCase

ACTIONS_RECORDING = (
    "Reading the task\n"
    "Writing the test\n"
    '{"schema_version": 1, "outcome": "done", "steps": 12, "usage": null, "session_id": "fake-session",'
    ' "duration_ms": 61000, "cost_usd": null, "error_class": null, "reset": null, "message": null}\n'
)
RESULT_OF_SCHEMA_1 = (
    '{"schema_version": 1, "outcome": "done", "steps": null, "usage": null, "session_id": "fake-session",'
    ' "duration_ms": 700183, "error_class": null, "reset": null, "message": "the client finished the task"}'
)


class RunsTestCase(RunTestCase):
    def run_deliver(self, *options: str):
        return self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), *options)

    def run_deliver_to_its_end(self) -> str:
        completed = self.run_deliver("--json")
        self.assertIn(completed.returncode, (0, 1, 3, 10, 12, 13), completed.stderr)
        return json.loads(completed.stdout)["run"]


class BrigadeRunsListOfAFinishedRunTest(RunsTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

    def test_should_list_the_run_with_its_state_and_outcome(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "runs": [
                    {
                        "run": run_id,
                        "procedure": "deliver",
                        "slot": "build",
                        "role": "builder",
                        "project": None,
                        "worktree": str(self.workspace),
                        "state": "finished",
                        "outcome": "done",
                        "wave": None,
                        "task": None,
                    }
                ],
                "skipped": [],
            },
        )


class BrigadeRunsShowOfAFinishedRunTest(RunsTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT + 'operations = "actions"\n')
        self.record_lines("builder", ACTIONS_RECORDING)

    def test_should_describe_the_run_and_its_segments_in_a_document(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "run": {
                    "run": run_id,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "project": None,
                    "worktree": str(self.workspace),
                    "state": "finished",
                    "outcome": "done",
                    "wave": None,
                    "task": None,
                    "message": None,
                },
                "segments": [{"segment": 1, "outcome": "done", "steps": 12, "duration_ms": ANY}],
                "journal": None,
                "progress": None,
            },
        )

    def test_should_print_the_summary_of_the_run_then_its_segments(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        lines = completed.stdout.splitlines()
        self.assertRegex(lines.pop(), r"^1        done     12     \d+m\d\ds$")
        self.assertEqual(
            lines,
            [
                f"run        {run_id}",
                "procedure  deliver",
                "slot       build",
                "role       builder",
                "project    -",
                "state      finished",
                "outcome    done",
                "message    -",
                "",
                "segment  outcome  steps  duration",
            ],
        )

    def test_should_exit_1_naming_the_line_of_the_journal_that_is_no_record_with_log(self):
        # Arrange
        rows = [
            ("a line of no JSON", "Reading the task\n", "not a JSON document"),
            ("a record lacking its time", '{"schema_version": 1, "segment": 1}\n', "lacks the key at"),
        ]
        for case, line, reason in rows:
            with self.subTest(case=case):
                # Arrange
                run_id = self.run_deliver_to_its_end()
                journal_path = self.runs / run_id / "journal.jsonl"
                with journal_path.open("a", encoding="utf-8") as journal:
                    journal.write(line)

                # Act
                completed = self.run_brigade("runs", "show", run_id, "--log")

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(
                    completed.stderr, f"brigade runs show: line 4 of {journal_path} is not a journal record: {reason}\n"
                )


class BrigadeRunsShowFollowOfAnEndedRunTest(RunsTestCase):
    def test_should_print_the_journal_as_log_does_then_the_state_and_outcome_of_the_run(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'operations = "actions"\n')
        self.record_lines("builder", ACTIONS_RECORDING)
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--follow")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stdout,
            rf"^run        {run_id}\n"
            r"procedure  deliver\nslot       build\nrole       builder\nproject    -\n"
            r"state      finished\noutcome    done\nmessage    -\n\n"
            r"segment  outcome  steps  duration\n1        done     12     \d+m\d\ds\n\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  text  Reading the task\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  text  Writing the test\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  result  done\n"
            r"\nstate      finished\noutcome    done\n$",
        )

    def test_should_refuse_json_as_a_usage_error(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--follow", "--json")

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "brigade runs show: --follow and --json exclude each other\n")


class BrigadeRunsStopOfARunningRunTest(RunsTestCase):
    def test_should_stop_a_detached_run_and_exit_0_once_it_finished_stopped(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + self.hold_the_client())
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver("--detach").stdout.strip()
        client_pid = self.wait_for_client(self.read_run_pid(run_id))

        # Act
        completed, [listed] = self.stop_the_run_and_list_the_runs(run_id)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, f"run {run_id} finished on stopped\n", completed.stderr)
        self.assert_process_gone(client_pid)
        self.assertEqual(listed["state"], "finished")
        self.assertEqual(listed["outcome"], "stopped")

    def stop_the_run_and_list_the_runs(self, run_id: str) -> tuple:
        return self.run_brigade("runs", "stop", run_id), self.list_the_runs()


class BrigadeRunsStopOfARunItCannotStopTest(RunsTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

    def test_should_refuse_a_finished_run_naming_its_outcome(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "stop", run_id)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, f"brigade runs stop: run {run_id} has already finished on done\n")


class BrigadeRunsOfARunWhoseResultIsOfAnOlderShapeTest(RunsTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        self.run_id = self.run_deliver_to_its_end()
        self.run_result = self.runs / self.run_id / "result.json"
        self.segment_result = self.runs / self.run_id / "segments" / "1" / "result.json"
        self.run_result.write_text(RESULT_OF_SCHEMA_1)
        self.segment_result.write_text(RESULT_OF_SCHEMA_1)

    def test_should_leave_it_out_of_the_list_and_name_it_on_stderr(self):
        # Act
        completed = self.run_brigade("runs", "list")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "no runs\n")
        self.assertEqual(
            completed.stderr,
            f"brigade runs list: skipped run {self.run_id}: {self.run_result} is not a run result:"
            " schema_version is 1, not one of 2\n",
        )


class BrigadeRunsListOfTheRunsOfAWaveOrOfATaskTest(RunsTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        self.run_task_of_wave("shop_w1", "S3")
        self.run_task_of_wave("shop_w1", "S4")
        self.s3_of_cafe = self.run_task_of_wave("cafe_w1", "S3")
        self.run_deliver_to_its_end()

    def run_task_of_wave(self, wave: str, task: str) -> str:
        completed = self.run_deliver("--wave", wave, "--task", task, "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)["run"]

    def test_should_print_the_runs_of_the_wave_as_a_table(self):
        # Act
        completed = self.run_brigade("runs", "list", "--wave", "cafe_w1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "run                      procedure  slot   role     project  state     outcome",
                f"{self.s3_of_cafe}  deliver    build  builder  -        finished  done",
            ],
        )
