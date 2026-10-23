import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from brigade.runs.detach_run import detach_run
from brigade.system.process_trace import SPAWNED, ProcessTrace
from brigade.system.trail_writer import TrailWriter
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.runs.create_run_plan import RUN_ID, create_run_plan


class SpawnedProcessDouble:
    pid = os.getpid()


class SpawnRecorderDouble:
    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return SpawnedProcessDouble()


class DetachRunTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.spawn = SpawnRecorderDouble()
        self.traces = []
        self.runtime = create_test_runtime(
            create_test_paths(self.root), spawn_process=self.spawn, trail=TrailWriter(self.traces.append)
        )


class DetachRunWithEveryOptionTest(DetachRunTestCase):
    def test_should_relaunch_brigade_run_with_the_options_of_the_plan(self):
        # Arrange
        plan = create_run_plan(
            self.root,
            project="tidepool",
            brief_path=Path("/home/ada/brief.md"),
            wave="w1",
            task="TP1",
            resumed=True,
            arguments={"task": "@TASK.TP1"},
        )
        plan.run_directory.mkdir(parents=True)

        # Act
        detach_run(plan, self.runtime)

        # Assert
        self.assertEqual(
            self.spawn.requests[0].argv,
            (
                sys.executable,
                "/srv/brigade/bin/brigade",
                "run",
                "build-task",
                "task=@TASK.TP1",
                "--slot",
                "build",
                "--cwd",
                str(self.root / "project"),
                "--project",
                "tidepool",
                "--brief",
                "/home/ada/brief.md",
                "--wave",
                "w1",
                "--task",
                "TP1",
                "--run-id",
                RUN_ID,
                "--resume",
            ),
        )


class DetachRunWithNoOptionTest(DetachRunTestCase):
    def test_should_log_the_detached_run_and_answer_its_pid(self):
        # Arrange
        plan = create_run_plan(self.root)
        plan.run_directory.mkdir(parents=True)

        # Act
        pid = detach_run(plan, self.runtime)

        # Assert
        request = self.spawn.requests[0]
        self.assertEqual(pid, os.getpid())
        self.assertEqual(request.stdout, plan.run_directory / "brigade.log")
        self.assertEqual(
            self.traces,
            [
                ProcessTrace(
                    argv=(
                        sys.executable,
                        "/srv/brigade/bin/brigade",
                        "run",
                        "build-task",
                        "--slot",
                        "build",
                        "--cwd",
                        str(self.root / "project"),
                        "--run-id",
                        RUN_ID,
                    ),
                    cwd=str(self.root / "project"),
                    outcome=SPAWNED,
                    exit_code=None,
                    duration_ms=None,
                    pid=os.getpid(),
                )
            ],
        )
