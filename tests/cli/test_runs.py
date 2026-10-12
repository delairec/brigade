import contextlib
import json
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from unittest.mock import ANY

from brigade.runs.record_run_pid import record_run_pid
from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, TURN_LIMIT_RESULT, RunTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT

UNKNOWN_RUN = "20990101T000000Z-abcdef"
ACTIONS_RECORDING = (
    "Reading the task\n"
    "Writing the test\n"
    '{"schema_version": 1, "outcome": "done", "steps": 12, "usage": null, "session_id": "fake-session",'
    ' "duration_ms": 61000, "cost_usd": null, "error_class": null, "reset": null, "message": null}\n'
)
FOLLOW_WAIT_S = 30
CLIENT_OUTLIVING_THE_TEST = 'delay = "120"\n'
LONGER_THAN_THE_DEFAULT_POLL_S = 3
BLANK_LINE = "\n"
END_OF_OUTPUT = ""
ANOTHER_START_TIME = 1


class RunsTestCase(RunTestCase):
    def run_deliver(self, *options: str):
        return self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), *options)

    def run_deliver_to_its_end(self) -> str:
        completed = self.run_deliver("--json")
        self.assertIn(completed.returncode, (0, 1, 3, 10, 12), completed.stderr)
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
        record_run_pid(self.runs / run_id, gone.pid)
        gone.wait()
        (self.runs / run_id / "result.json").unlink()

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
                    "state": "finished",
                    "outcome": "done",
                },
                "segments": [{"segment": 1, "outcome": "done"}],
                "journal": None,
            },
        )

    def test_should_print_the_summary_of_the_run_then_its_segments(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                f"run        {run_id}",
                "procedure  deliver",
                "slot       build",
                "role       builder",
                "project    -",
                "state      finished",
                "outcome    done",
                "",
                "segment  outcome",
                "1        done",
            ],
        )

    def test_should_add_the_journal_of_the_actions_in_order_with_log(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--log", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["journal"],
            [
                {
                    "schema_version": 1,
                    "at": ANY,
                    "segment": 1,
                    "kind": "text",
                    "summary": "Reading the task",
                    "cut": False,
                },
                {
                    "schema_version": 1,
                    "at": ANY,
                    "segment": 1,
                    "kind": "text",
                    "summary": "Writing the test",
                    "cut": False,
                },
                {"schema_version": 1, "at": ANY, "segment": 1, "kind": "result", "summary": "done", "cut": False},
            ],
        )

    def test_should_print_one_line_per_record_giving_its_time_segment_kind_and_summary_with_log(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--log")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stdout,
            r"\n1        done\n\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  text  Reading the task\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  text  Writing the test\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  result  done\n$",
        )

    def test_should_leave_out_the_record_still_being_written_with_log(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()
        with (self.runs / run_id / "journal.jsonl").open("a", encoding="utf-8") as journal:
            journal.write('{"schema_version": 1, "at": "2026-')

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--log", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["journal"],
            [
                {
                    "schema_version": 1,
                    "at": ANY,
                    "segment": 1,
                    "kind": "text",
                    "summary": "Reading the task",
                    "cut": False,
                },
                {
                    "schema_version": 1,
                    "at": ANY,
                    "segment": 1,
                    "kind": "text",
                    "summary": "Writing the test",
                    "cut": False,
                },
                {"schema_version": 1, "at": ANY, "segment": 1, "kind": "result", "summary": "done", "cut": False},
            ],
        )

    def test_should_exit_1_naming_the_line_of_the_journal_that_is_no_record_with_log(self):
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

    def test_should_exit_1_naming_an_unknown_run(self):
        rows = [("an unknown id", UNKNOWN_RUN), ("a path", "../runs")]
        for case, run_id in rows:
            with self.subTest(case=case):
                # Act
                completed = self.run_brigade("runs", "show", run_id)

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, f"brigade runs show: no run {run_id}\n")

    def test_should_exit_1_naming_a_path_to_a_run_rather_than_its_id(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()
        path_to_the_run = f"../runs/{run_id}"

        # Act
        completed = self.run_brigade("runs", "show", path_to_the_run)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, f"brigade runs show: no run {path_to_the_run}\n")

    def test_should_show_a_dead_run_with_no_segment_and_an_empty_journal(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()
        gone = subprocess.Popen(["true"])  # noqa: S607 - true found on the PATH of the test
        record_run_pid(self.runs / run_id, gone.pid)
        gone.wait()
        (self.runs / run_id / "result.json").unlink()
        (self.runs / run_id / "journal.jsonl").unlink()
        shutil.rmtree(self.runs / run_id / "segments")

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--log", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual((document["run"]["state"], document["segments"], document["journal"]), ("dead", [], []))


class BrigadeRunJournalOfAClientWithNoActionsOperationTest(RunsTestCase):
    def test_should_hold_one_raw_record_per_line_cut_to_200_characters(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--log", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["journal"],
            [
                {
                    "schema_version": 1,
                    "at": ANY,
                    "segment": 1,
                    "kind": "raw",
                    "summary": (
                        '{"schema_version": 1, "outcome": "done", "steps": 12, "usage": {"input_tokens": 120,'
                        ' "output_tokens": 3400, "cache_creation_input_tokens": 16778, "cache_read_input_tokens":'
                        ' 98000}, "session_id": "fake'
                    ),
                    "cut": True,
                }
            ],
        )


class BrigadeRunsShowOfARunHandedOverTest(RunsTestCase):
    def test_should_list_the_segments_in_their_order(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", TURN_LIMIT_RESULT)
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["segments"],
            [
                {"segment": 1, "outcome": "turn_limit"},
                {"segment": 2, "outcome": "turn_limit"},
                {"segment": 3, "outcome": "turn_limit"},
            ],
        )


class BrigadeRunsShowOfARunningRunTest(RunsTestCase):
    def test_should_show_the_running_segment_with_no_outcome_and_no_record_yet(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'delay = "2"\n')
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver("--detach").stdout.strip()
        self.wait_for_file(self.runs / run_id / "segments" / "1" / "brief.md")

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--log", "--json")

        # Assert
        self.wait_for_file(self.runs / run_id / "result.json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            (document["run"]["state"], document["segments"], document["journal"]),
            ("running", [{"segment": 1, "outcome": None}], []),
        )


class BrigadeRunJournalOfADetachedRunTest(RunsTestCase):
    def test_should_gain_records_while_the_client_writes_its_lines(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'operations = "actions"\ninterval = "1"\n', keys="journal_poll_s = 0.1\n")
        self.record_lines("builder", ACTIONS_RECORDING)
        run_id = self.run_deliver("--detach").stdout.strip()

        # Act
        self.wait_for_line(self.runs / run_id / "journal.jsonl")

        # Assert
        finished_before_its_first_record = (self.runs / run_id / "result.json").exists()
        self.wait_for_file(self.runs / run_id / "result.json")
        self.assertFalse(finished_before_its_first_record)


class RunsFollowTestCase(RunsTestCase):
    def start_follow(self, run_id: str) -> subprocess.Popen:
        follow = subprocess.Popen(  # noqa: S603 - the test's own command line
            [sys.executable, str(CLONE_ENTRY_POINT), "runs", "show", run_id, "--follow"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(follow.kill)
        return follow

    def interrupt_after(self, follow: subprocess.Popen, delay_s: float) -> str:
        with contextlib.suppress(subprocess.TimeoutExpired):
            follow.wait(timeout=delay_s)
        follow.send_signal(signal.SIGINT)
        return follow.communicate(timeout=FOLLOW_WAIT_S)[0]

    def read_through_blank_line(self, follow: subprocess.Popen) -> None:
        while follow.stdout.readline() not in (BLANK_LINE, END_OF_OUTPUT):
            pass

    def read_opening(self, follow: subprocess.Popen) -> None:
        self.read_through_blank_line(follow)
        self.read_through_blank_line(follow)


class BrigadeRunsShowFollowOfARunningRunTest(RunsFollowTestCase):
    def test_should_print_a_record_written_after_it_started_and_exit_0_once_the_run_is_done(self):
        # Arrange
        self.configure_fake(
            COUNTING_CLIENT + 'operations = "actions"\ndelay = "1"\ninterval = "1"\n', keys="journal_poll_s = 0.1\n"
        )
        self.record_lines("builder", ACTIONS_RECORDING)
        run_id = self.run_deliver("--detach").stdout.strip()
        journal_path = self.runs / run_id / "journal.jsonl"
        journal_path.touch()
        follow = self.start_follow(run_id)
        self.read_opening(follow)
        journal_at_opening = journal_path.read_text()

        # Act
        stdout, stderr = follow.communicate(timeout=FOLLOW_WAIT_S)

        # Assert
        self.assertEqual(follow.returncode, 0, stderr)
        self.assertNotIn("Writing the test", journal_at_opening)
        self.assertRegex(
            stdout,
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  text  Reading the task\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  text  Writing the test\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  result  done\n"
            r"\nstate      finished\noutcome    done\n$",
        )

    def test_should_read_the_run_again_only_every_journal_poll_s_seconds(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'delay = "2"\n', keys="journal_poll_s = 3600\n")
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver("--detach").stdout.strip()
        follow = self.start_follow(run_id)
        self.read_opening(follow)
        self.wait_for_file(self.runs / run_id / "result.json")

        # Act
        stdout = self.interrupt_after(follow, LONGER_THAN_THE_DEFAULT_POLL_S)

        # Assert
        self.assertEqual(stdout, "\nstate      running\noutcome    -\n")

    def test_should_exit_0_on_a_signal_and_leave_the_run_running(self):
        rows = [("SIGINT", signal.SIGINT), ("SIGTERM", signal.SIGTERM)]
        for name, stop_signal in rows:
            with self.subTest(signal=name):
                # Arrange
                self.configure_fake(COUNTING_CLIENT + 'delay = "5"\n', keys="journal_poll_s = 0.1\n")
                self.record("builder", DONE_RESULT)
                run_id = self.run_deliver("--detach").stdout.strip()
                follow = self.start_follow(run_id)
                self.read_opening(follow)

                # Act
                follow.send_signal(stop_signal)

                # Assert
                stdout, stderr = follow.communicate(timeout=FOLLOW_WAIT_S)
                shown = self.run_brigade("runs", "show", run_id, "--json")
                self.wait_for_file(self.runs / run_id / "result.json")
                self.assertEqual((follow.returncode, stderr), (0, ""))
                self.assertEqual(stdout, "\nstate      running\noutcome    -\n")
                self.assertEqual(json.loads(shown.stdout)["run"]["state"], "running")


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
            r"state      finished\noutcome    done\n\n"
            r"segment  outcome\n1        done\n\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  text  Reading the task\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  text  Writing the test\n"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z  1  result  done\n"
            r"\nstate      finished\noutcome    done\n$",
        )

    def test_should_exit_as_brigade_run_does_by_the_outcome_of_the_run(self):
        rows = [
            ("done", DONE_RESULT, 0, "outcome    done"),
            ("failed", {**TURN_LIMIT_RESULT, "error_class": "execution"}, 1, "outcome    failed"),
            ("undeclared", {**DONE_RESULT, "outcome": "undeclared"}, 3, "outcome    undeclared"),
            ("blocked", {**DONE_RESULT, "outcome": "blocked"}, 10, "outcome    blocked"),
            ("turn limit", TURN_LIMIT_RESULT, 12, "outcome    turn_limit"),
        ]
        for case, result, exit_code, outcome_line in rows:
            with self.subTest(case=case):
                # Arrange
                self.configure_fake(COUNTING_CLIENT)
                self.record("builder", result)
                run_id = self.run_deliver_to_its_end()

                # Act
                completed = self.run_brigade("runs", "show", run_id, "--follow")

                # Assert
                self.assertEqual(completed.returncode, exit_code, completed.stderr)
                self.assertEqual(completed.stdout.splitlines()[-3:], ["", "state      finished", outcome_line])

    def test_should_exit_1_once_it_sees_the_run_dead(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver_to_its_end()
        gone = subprocess.Popen(["true"])  # noqa: S607 - true found on the PATH of the test
        record_run_pid(self.runs / run_id, gone.pid)
        gone.wait()
        (self.runs / run_id / "result.json").unlink()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--follow")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(completed.stdout.splitlines()[-3:], ["", "state      dead", "outcome    -"])

    def test_should_refuse_json_as_a_usage_error(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver_to_its_end()

        # Act
        completed = self.run_brigade("runs", "show", run_id, "--follow", "--json")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (2, "", "brigade runs show: --follow and --json exclude each other\n"),
        )


class BrigadeRunsStopOfARunningRunTest(RunsTestCase):
    def test_should_stop_a_detached_run_and_exit_0_once_it_finished_stopped(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + CLIENT_OUTLIVING_THE_TEST)
        self.record("builder", DONE_RESULT)
        run_id = self.run_deliver("--detach").stdout.strip()
        client_pid = self.wait_for_client(self.read_run_pid(run_id))

        # Act
        completed = self.run_brigade("runs", "stop", run_id)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout), (0, f"run {run_id} finished on stopped\n"), completed.stderr
        )
        self.assert_process_gone(client_pid)
        [listed] = json.loads(self.run_brigade("runs", "list", "--json").stdout)["runs"]
        self.assertEqual((listed["state"], listed["outcome"]), ("finished", "stopped"))


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
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade runs stop: run {run_id} has already finished on done\n"),
        )

    def test_should_refuse_a_run_holding_no_pid_file(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()
        (self.runs / run_id / "result.json").unlink()
        (self.runs / run_id / "pid").unlink()

        # Act
        completed = self.run_brigade("runs", "stop", run_id)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade runs stop: run {run_id} holds no pid file naming its process\n"),
        )

    def test_should_refuse_a_dead_run_naming_the_pid_no_process_holds(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()
        gone = subprocess.Popen(["true"])  # noqa: S607 - true found on the PATH of the test
        record_run_pid(self.runs / run_id, gone.pid)
        gone.wait()
        (self.runs / run_id / "result.json").unlink()

        # Act
        completed = self.run_brigade("runs", "stop", run_id)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade runs stop: run {run_id} is dead: no process of its identity holds its pid {gone.pid}\n"),
        )

    def test_should_refuse_a_run_whose_pid_holds_a_process_of_another_start_time_and_signal_none(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()
        stranger = subprocess.Popen(["sleep", "120"])  # noqa: S607 - sleep found on the PATH of the test
        self.addCleanup(stranger.wait)
        self.addCleanup(stranger.kill)
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        (self.runs / run_id / "result.json").unlink()
        (self.runs / run_id / "pid").write_text(f"{stranger.pid} {ANOTHER_START_TIME} {boot_id}\n")

        # Act
        completed = self.run_brigade("runs", "stop", run_id)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (
                1,
                "",
                f"brigade runs stop: run {run_id} is dead: no process of its identity holds its pid {stranger.pid}\n",
            ),
        )
        self.assertIsNone(stranger.poll())

    def test_should_refuse_an_unknown_run(self):
        # Act
        completed = self.run_brigade("runs", "stop", UNKNOWN_RUN)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade runs stop: no run {UNKNOWN_RUN}\n"),
        )

    def test_should_report_a_run_its_signal_left_dead_and_exit_1(self):
        # Arrange
        run_id = self.run_deliver_to_its_end()
        orphan = subprocess.run(
            ["sh", "-c", "sleep 120 >/dev/null 2>&1 & echo $!"],  # noqa: S607 - sh found on the PATH of the test
            capture_output=True,
            text=True,
            check=True,
        )
        (self.runs / run_id / "result.json").unlink()
        record_run_pid(self.runs / run_id, int(orphan.stdout))

        # Act
        completed = self.run_brigade("runs", "stop", run_id)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade runs stop: run {run_id} ended dead, not stopped\n"),
        )
