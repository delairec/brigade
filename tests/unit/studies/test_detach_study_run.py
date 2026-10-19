import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.studies.detach_study_run import detach_study_run
from brigade.system.spawn_process import SpawnRequest
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"


class DetachStudyRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.spawned = []
        self.runtime = create_scripted_runtime(self.root, ScriptedProcesses(), spawn_process=self.spawn)

    def spawn(self, request: SpawnRequest) -> SimpleNamespace:
        self.spawned.append(request)
        return SimpleNamespace(pid=os.getpid())

    def test_should_run_the_study_in_a_detached_brigade_logging_into_its_run(self):
        # Act
        detach_study_run(self.runtime, "trees", RUN_ID)

        # Assert
        log = self.root / "state" / "runs" / RUN_ID / "brigade.log"
        self.assertEqual(
            self.spawned,
            [
                SpawnRequest(
                    argv=(
                        sys.executable,
                        str(self.root / "bin" / "brigade"),
                        "study",
                        "run",
                        "trees",
                        "--run-id",
                        RUN_ID,
                    ),
                    cwd=str(self.root / "config"),
                    environment={},
                    stdin=None,
                    stdout=log,
                    stderr=log,
                )
            ],
        )

    def test_should_answer_the_pid_of_the_detached_brigade(self):
        # Act
        pid = detach_study_run(self.runtime, "trees", RUN_ID)

        # Assert
        self.assertEqual(pid, os.getpid())
