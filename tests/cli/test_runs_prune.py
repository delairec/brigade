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
