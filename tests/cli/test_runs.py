import json
import subprocess

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, TURN_LIMIT_RESULT, RunTestCase

UNKNOWN_RUN = "20990101T000000Z-abcdef"


class RunsTestCase(RunTestCase):
    def run_deliver(self, *options: str):
        return self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), *options)

    def run_deliver_to_its_end(self) -> str:
        completed = self.run_deliver("--json")
        self.assertIn(completed.returncode, (0, 1), completed.stderr)
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
                        "state": "finished",
                        "outcome": "done",
                    }
                ],
            },
        )

    def test_should_print_the_runs_as_a_table_under_its_header(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "list")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "run                      procedure  slot   role     project  state     outcome",
                f"{run_id}  deliver    build  builder  -        finished  done",
            ],
        )

    def test_should_list_a_run_whose_process_is_gone_without_a_result_as_dead(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()
        gone = subprocess.Popen(["true"])  # noqa: S607 - true found on the PATH of the test
        gone.wait()
        (self.runs / run_id / "result.json").unlink()
        (self.runs / run_id / "pid").write_text(f"{gone.pid}\n")

        # Act
        completed = self.run_brigade("runs", "list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [listed] = json.loads(completed.stdout)["runs"]
        self.assertEqual(listed["state"], "dead")


class BrigadeRunsListOfARunningRunTest(RunsTestCase):
    def test_should_list_a_detached_run_whose_client_has_not_finished_as_running(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'delay = "2"\n')
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver("--detach").stdout.strip()

        # Act
        completed = self.run_brigade("runs", "list", "--json")

        # Assert
        self.wait_for_file(self.runs / run_id / "result.json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [listed] = json.loads(completed.stdout)["runs"]
        self.assertEqual(listed["state"], "running")


class BrigadeRunsLogsTest(RunsTestCase):
    def test_should_print_the_output_of_the_client_as_a_document(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "logs", run_id, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout), {"schema_version": 1, "run": run_id, "lines": [json.dumps(DONE_RESULT)]}
        )

    def test_should_print_the_output_of_the_client_as_text(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "logs", run_id)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, json.dumps(DONE_RESULT) + "\n")

    def test_should_print_the_last_lines_of_every_segment_with_tail(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", TURN_LIMIT_RESULT)
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "logs", run_id, "--tail", "2", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "run": run_id,
                "lines": [json.dumps(TURN_LIMIT_RESULT), json.dumps(TURN_LIMIT_RESULT)],
            },
        )

    def test_should_exit_1_naming_an_unknown_run(self):
        # Act
        completed = self.run_brigade("runs", "logs", UNKNOWN_RUN)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, f"brigade runs logs: no run {UNKNOWN_RUN}\n")
