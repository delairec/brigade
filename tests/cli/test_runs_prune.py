import json

from brigade.runs.record_run_pid import record_run_pid
from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, RunTestCase
from tests.process_launcher import ProcessLauncher


class BrigadeRunsPruneTest(RunTestCase):
    def deliver(self) -> str:
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json"
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)["run"]

    def make_dead(self, run_id: str) -> None:
        gone = ProcessLauncher.start(["true"])
        record_run_pid(self.runs / run_id, gone.pid)
        gone.wait()
        (self.runs / run_id / "result.json").unlink()

    def test_should_remove_the_runs_beyond_keep_and_print_each_in_a_document(self):
        # Arrange
        oldest = self.deliver()
        dead = self.deliver()
        self.make_dead(dead)
        newest = self.deliver()

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
        self.assertEqual(completed.stderr, "")
        self.assertEqual(list(self.runs.iterdir()), [self.runs / newest])
