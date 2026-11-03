import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path

from brigade.runs.detach_brigade_command import DetachedCommand, detach_brigade_command
from brigade.system.spawn_process import SpawnRequest
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.spawned_process_double import SpawnedProcessDouble

DETACHED_PID = 4242


class DetachBrigadeCommandTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.spawned = []
        self.recorded_pids = []

    def spawn(self, request: SpawnRequest) -> SpawnedProcessDouble:
        self.spawned.append(request)
        return SpawnedProcessDouble(pid=DETACHED_PID)

    def record_pid(self, run_directory: Path, pid: int) -> None:
        self.recorded_pids.append((run_directory, pid))

    def detach_on_a_session_bus(self, session_bus_address: str | None) -> None:
        paths = dataclasses.replace(create_test_paths(self.root), session_bus_address=session_bus_address)
        runtime = create_test_runtime(paths, spawn_process=self.spawn)
        detached = DetachedCommand(command=("run", "build-task"), cwd="/srv/project", run_directory=self.root / "r1")
        detach_brigade_command(runtime, detached, self.record_pid)

    def test_should_hand_the_session_bus_of_brigade_to_the_brigade_it_detaches(self):
        # Act
        self.detach_on_a_session_bus("unix:path=/run/user/1000/bus")

        # Assert
        self.assertEqual(
            self.spawned,
            [
                SpawnRequest(
                    argv=(sys.executable, "/srv/brigade/bin/brigade", "run", "build-task"),
                    cwd="/srv/project",
                    environment={"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
                    stdin=None,
                    stdout=self.root / "r1" / "brigade.log",
                    stderr=self.root / "r1" / "brigade.log",
                )
            ],
        )

    def test_should_hand_no_variable_to_the_brigade_it_detaches_when_brigade_has_no_session_bus(self):
        # Arrange
        no_session_bus = None

        # Act
        self.detach_on_a_session_bus(no_session_bus)

        # Assert
        self.assertEqual(self.spawned[0].environment, {})
