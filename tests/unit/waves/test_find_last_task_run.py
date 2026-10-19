import unittest

from brigade.ledger.run_finished import RunFinished
from brigade.ledger.wave_resumed import WaveResumed
from brigade.waves.find_last_task_run import find_last_task_run


def create_finished_run(run: str, project: str, task: str) -> RunFinished:
    return RunFinished(
        run=run,
        segment=1,
        procedure="awawa-task",
        slot="build",
        role="ada",
        client="claude-code",
        project=project,
        session=None,
        main_steps=None,
        total_steps=None,
        duration_ms=None,
        usage=None,
        outcome="done",
        error_class=None,
        exit=0,
        wave="oak_w1",
        task=task,
        nulls={},
    )


class FindLastTaskRunTest(unittest.TestCase):
    def test_should_find_the_last_run_of_the_task_of_the_project(self):
        # Arrange
        events = (
            create_finished_run("r1", "oak", "B12"),
            create_finished_run("r2", "oak", "B12"),
            create_finished_run("r3", "oak", "B13"),
            create_finished_run("r4", "elm", "B12"),
            WaveResumed(wave="oak_w1", reason="quota"),
        )

        # Act
        run = find_last_task_run(events, "oak", "B12")

        # Assert
        self.assertEqual(run, "r2")

    def test_should_find_no_run_of_a_task_never_run(self):
        # Arrange
        events = (create_finished_run("r1", "oak", "B13"),)

        # Act
        run = find_last_task_run(events, "oak", "B12")

        # Assert
        self.assertIsNone(run)
