import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.studies.detach_study_run import detach_study_run
from brigade.system.spawn_process import SpawnRequest
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
DETACHED_PID = 4242


class DetachStudyRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.spawned = []
        self.recorded_pids = []
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(
            create_test_paths(self.root), run_process=ScriptedProcesses(), spawn_process=self.spawn
        )

    def spawn(self, request: SpawnRequest) -> SimpleNamespace:
        self.spawned.append(request)
        return SimpleNamespace(pid=DETACHED_PID)

    def record_pid(self, run_directory: Path, pid: int) -> None:
        self.recorded_pids.append((run_directory, pid))

    def test_should_run_the_study_in_a_detached_brigade_logging_into_its_run(self):
        # Act
        detach_study_run(self.runtime, "trees", RUN_ID, self.record_pid)

        # Assert
        log = self.root / "state" / "runs" / RUN_ID / "brigade.log"
        self.assertEqual(
            self.spawned,
            [
                SpawnRequest(
                    argv=(
                        sys.executable,
                        "/srv/brigade/bin/brigade",
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
        pid = detach_study_run(self.runtime, "trees", RUN_ID, self.record_pid)

        # Assert
        self.assertEqual(pid, 4242)

    def test_should_record_the_pid_of_the_detached_brigade_in_its_run(self):
        # Act
        detach_study_run(self.runtime, "trees", RUN_ID, self.record_pid)

        # Assert
        self.assertEqual(self.recorded_pids, [(self.root / "state" / "runs" / RUN_ID, 4242)])
