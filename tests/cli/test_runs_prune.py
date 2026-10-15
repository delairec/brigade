import json
import os

from brigade.runs.record_run_pid import record_run_pid
from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, RunTestCase
from tests.process_launcher import ProcessLauncher

RATE_LIMIT_RESULT = {
    "schema_version": 1,
    "outcome": "failed",
    "steps": 30,
    "usage": None,
    "session_id": "fake-session",
    "duration_ms": 20000,
    "cost_usd": None,
    "error_class": "rate_limit",
    "reset": None,
    "message": "You've hit your limit",
}
CLIENT_OUTLIVING_THE_TEST = 'delay = "120"\n'
JANUARY_2020 = 1577836800
JANUARY_2026 = 1767225600
UNREADABLE_RUN = "unreadable-run"
ANOTHER_UNREADABLE_RUN = "another-unreadable-run"
INTERRUPTED_REMOVAL = "interrupted-run"


class RunsPruneTestCase(RunTestCase):
    def deliver(self, result: dict, keys: str = "") -> str:
        self.configure_fake(COUNTING_CLIENT, keys=keys)
        self.record("builder", result)
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json"
        )
        self.assertIn(completed.returncode, (0, 1), completed.stderr)
        return json.loads(completed.stdout)["run"]

    def start_running_run(self) -> str:
        self.configure_fake(COUNTING_CLIENT + CLIENT_OUTLIVING_THE_TEST)
        self.record("builder", DONE_RESULT)
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--detach"
        )
        run_id = completed.stdout.strip()
        self.wait_for_client(self.read_run_pid(run_id))
        self.addCleanup(self.run_brigade, "runs", "stop", run_id)
        return run_id

    def make_dead(self, run_id: str) -> None:
        gone = ProcessLauncher.start(["true"])
        record_run_pid(self.runs / run_id, gone.pid)
        gone.wait()
        (self.runs / run_id / "result.json").unlink()

    def date_result(self, run_id: str, instant: int) -> None:
        os.utime(self.runs / run_id / "result.json", (instant, instant))

    def list_kept_runs(self) -> set[str]:
        return {path.name for path in self.runs.iterdir()}

    def list_removed_runs(self) -> set[str]:
        return {path.name for path in self.removed_runs.iterdir()}

    @property
    def removed_runs(self):
        return self.runs.parent / "runs-removed"

    @property
    def unreadable_record(self):
        return self.runs / UNREADABLE_RUN / "run.json"

    def plant_unreadable_run(self, run: str = UNREADABLE_RUN) -> None:
        (self.runs / run).mkdir(parents=True)
        (self.runs / run / "run.json").write_text("not a run record")

    def plant_interrupted_removal(self) -> None:
        (self.removed_runs / INTERRUPTED_REMOVAL).mkdir(parents=True)
        (self.removed_runs / INTERRUPTED_REMOVAL / "run.json").write_text("{}")

    def forbid_writing(self, directory) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o500)

    def plant_undeletable_removal(self) -> None:
        locked = self.removed_runs / INTERRUPTED_REMOVAL / "segments"
        locked.mkdir(parents=True)
        (locked / "stdout.log").write_text("")
        self.forbid_writing(locked)


class BrigadeRunBoundsTheRunsTest(RunsPruneTestCase):
    def test_should_remove_the_oldest_finished_run_beyond_the_runs_kept_of_the_configuration(self):
        # Arrange
        oldest = self.deliver(DONE_RESULT, keys="runs_kept = 1\n")

        # Act
        newest = self.deliver(DONE_RESULT, keys="runs_kept = 1\n")

        # Assert
        self.assertNotEqual(oldest, newest)
        self.assertEqual(self.list_kept_runs(), {newest})

    def test_should_keep_every_run_within_the_default_bound(self):
        # Arrange
        oldest = self.deliver(DONE_RESULT)

        # Act
        newest = self.deliver(DONE_RESULT)

        # Assert
        self.assertEqual(self.list_kept_runs(), {oldest, newest})

    def test_should_remove_a_dead_run_beyond_the_bound(self):
        # Arrange
        dead = self.deliver(DONE_RESULT, keys="runs_kept = 1\n")
        self.make_dead(dead)

        # Act
        newest = self.deliver(DONE_RESULT, keys="runs_kept = 1\n")

        # Assert
        self.assertEqual(self.list_kept_runs(), {newest})

    def test_should_keep_a_running_run_without_counting_it(self):
        # Arrange
        running = self.start_running_run()

        # Act
        newest = self.deliver(DONE_RESULT, keys="runs_kept = 1\n")

        # Assert
        self.assertEqual(self.list_kept_runs(), {running, newest})

    def test_should_keep_a_rate_limited_run_the_resume_takes_up_without_counting_it(self):
        # Arrange
        rate_limited = self.deliver(RATE_LIMIT_RESULT, keys="runs_kept = 1\n")

        # Act
        newest = self.deliver(DONE_RESULT, keys="runs_kept = 1\n")

        # Assert
        self.assertEqual(self.list_kept_runs(), {rate_limited, newest})

    def test_should_refuse_a_runs_kept_below_1_naming_the_key_and_the_file(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT, keys="runs_kept = 0\n")
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace))

        # Assert
        configuration = self.machine.corpus / "config.toml"
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn(f"runs_kept is 0, not 1 or more, in {configuration}", completed.stderr)

    def test_should_skip_an_unreadable_run_naming_it_and_keep_its_exit_code(self):
        # Arrange
        self.plant_unreadable_run()
        self.configure_fake(COUNTING_CLIENT, keys="runs_kept = 1\n")
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(
            f"brigade run: run unreadable-run skipped, {self.unreadable_record} is not a run record: not a JSON document",
            completed.stderr,
        )
        self.assertEqual(self.list_kept_runs(), {UNREADABLE_RUN, json.loads(completed.stdout)["run"]})


class BrigadeRunsPruneTest(RunsPruneTestCase):
    def test_should_remove_the_runs_beyond_keep_and_print_each_in_a_document(self):
        # Arrange
        oldest = self.deliver(DONE_RESULT)
        dead = self.deliver(DONE_RESULT)
        self.make_dead(dead)
        newest = self.deliver(DONE_RESULT)

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "dry_run": False,
                "runs": [{"run": oldest, "state": "finished"}, {"run": dead, "state": "dead"}],
                "skipped": [],
            },
        )
        self.assertEqual(self.list_kept_runs(), {newest})

    def test_should_print_each_run_removed_on_a_line(self):
        # Arrange
        oldest = self.deliver(DONE_RESULT)
        self.deliver(DONE_RESULT)

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, f"removed {oldest} (finished)\n"))

    def test_should_say_so_when_no_run_is_removed(self):
        # Arrange
        self.deliver(DONE_RESULT)

        # Act
        completed = self.run_brigade("runs", "prune")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, "no run removed\n"))

    def test_should_print_what_would_go_and_remove_nothing_on_a_dry_run(self):
        # Arrange
        oldest = self.deliver(DONE_RESULT)
        newest = self.deliver(DONE_RESULT)

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1", "--dry-run")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, f"would remove {oldest} (finished)\n"))
        self.assertEqual(self.list_kept_runs(), {oldest, newest})

    def test_should_remove_every_run_older_than_the_date_whatever_their_number(self):
        # Arrange
        old = self.deliver(DONE_RESULT)
        self.date_result(old, JANUARY_2020)
        recent = self.deliver(DONE_RESULT)
        self.date_result(recent, JANUARY_2026)

        # Act
        completed = self.run_brigade("runs", "prune", "--before", "2021-01-01", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["runs"], [{"run": old, "state": "finished"}])
        self.assertEqual(self.list_kept_runs(), {recent})

    def test_should_remove_the_runs_beyond_keep_and_those_settled_before_the_day(self):
        # Arrange
        old = self.deliver(DONE_RESULT)
        self.date_result(old, JANUARY_2020)
        older_recent = self.deliver(DONE_RESULT)
        self.date_result(older_recent, JANUARY_2026)
        newest = self.deliver(DONE_RESULT)

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1", "--before", "2021-01-01", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["runs"],
            [{"run": old, "state": "finished"}, {"run": older_recent, "state": "finished"}],
        )
        self.assertEqual(self.list_kept_runs(), {newest})

    def test_should_take_the_runs_lock(self):
        # Arrange
        self.deliver(DONE_RESULT)

        # Act
        completed = self.run_brigade("runs", "prune")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex((self.runs.parent / "locks" / "runs.lock").read_text(), r"\A[0-9]+\n\Z")

    def test_should_leave_a_run_whole_in_runs_when_it_cannot_move_it_out(self):
        # Arrange
        oldest = self.deliver(DONE_RESULT)
        newest = self.deliver(DONE_RESULT)
        self.forbid_writing(self.removed_runs)

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, f"brigade runs prune: cannot write {self.removed_runs}: Permission denied\n"),
        )
        self.assertEqual(self.list_kept_runs(), {oldest, newest})

    def test_should_first_empty_what_an_interrupted_removal_left(self):
        # Arrange
        self.plant_interrupted_removal()

        # Act
        completed = self.run_brigade("runs", "prune")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.list_removed_runs(), set())

    def test_should_empty_a_file_an_interrupted_removal_left(self):
        # Arrange
        self.removed_runs.mkdir(parents=True)
        (self.removed_runs / "stray-file").write_text("")

        # Act
        completed = self.run_brigade("runs", "prune")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.list_removed_runs(), set())

    def test_should_name_what_an_interrupted_removal_left_when_it_cannot_delete_it(self):
        # Arrange
        self.plant_undeletable_removal()

        # Act
        completed = self.run_brigade("runs", "prune")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, f"brigade runs prune: cannot write {self.removed_runs / INTERRUPTED_REMOVAL}: Permission denied\n"),
        )

    def test_should_leave_a_run_whole_in_runs_when_it_cannot_create_the_removed_runs_directory(self):
        # Arrange
        oldest = self.deliver(DONE_RESULT)
        newest = self.deliver(DONE_RESULT)
        self.removed_runs.write_text("")

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, f"brigade runs prune: cannot write {self.removed_runs}: File exists\n"),
        )
        self.assertEqual(self.list_kept_runs(), {oldest, newest})

    def test_should_name_the_unreadable_runs_in_the_order_of_their_names(self):
        # Arrange
        self.plant_unreadable_run(ANOTHER_UNREADABLE_RUN)
        self.plant_unreadable_run(UNREADABLE_RUN)

        # Act
        completed = self.run_brigade("runs", "prune", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["skipped"],
            [
                {
                    "run": "another-unreadable-run",
                    "reason": f"{self.runs / ANOTHER_UNREADABLE_RUN / 'run.json'} is not a run record: not a JSON document",
                },
                {
                    "run": "unreadable-run",
                    "reason": f"{self.unreadable_record} is not a run record: not a JSON document",
                },
            ],
        )

    def test_should_leave_what_an_interrupted_removal_left_on_a_dry_run(self):
        # Arrange
        self.plant_interrupted_removal()

        # Act
        completed = self.run_brigade("runs", "prune", "--dry-run")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.list_removed_runs(), {INTERRUPTED_REMOVAL})

    def test_should_skip_an_unreadable_run_naming_it_on_stderr(self):
        # Arrange
        oldest = self.deliver(DONE_RESULT)
        newest = self.deliver(DONE_RESULT)
        self.plant_unreadable_run()

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "dry_run": False,
                "runs": [{"run": oldest, "state": "finished"}],
                "skipped": [
                    {
                        "run": "unreadable-run",
                        "reason": f"{self.unreadable_record} is not a run record: not a JSON document",
                    }
                ],
            },
        )
        self.assertEqual(
            completed.stderr,
            f"brigade runs prune: run unreadable-run skipped, {self.unreadable_record} is not a run record: not a JSON document\n",
        )
        self.assertEqual(self.list_kept_runs(), {UNREADABLE_RUN, newest})

    def test_should_keep_a_rate_limited_run_without_counting_it(self):
        # Arrange
        rate_limited = self.deliver(RATE_LIMIT_RESULT)
        newest = self.deliver(DONE_RESULT)

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, "no run removed\n"))
        self.assertEqual(self.list_kept_runs(), {rate_limited, newest})

    def test_should_remove_a_rate_limited_run_as_well_when_asked_for_the_resumable_runs(self):
        # Arrange
        rate_limited = self.deliver(RATE_LIMIT_RESULT)
        newest = self.deliver(DONE_RESULT)

        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "1", "--resumable")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, f"removed {rate_limited} (finished)\n"))
        self.assertEqual(self.list_kept_runs(), {newest})

    def test_should_never_remove_a_running_run(self):
        # Arrange
        running = self.start_running_run()

        # Act
        completed = self.run_brigade("runs", "prune", "--before", "2099-01-01", "--resumable")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, "no run removed\n"))
        self.assertEqual(self.list_kept_runs(), {running})

    def test_should_remove_nothing_on_a_machine_that_never_ran_one(self):
        # Act
        completed = self.run_brigade("runs", "prune")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, "no run removed\n"), completed.stderr)

    def test_should_refuse_a_keep_below_1(self):
        # Act
        completed = self.run_brigade("runs", "prune", "--keep", "0")

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--keep: '0' is not a count of 1 or more", completed.stderr)
