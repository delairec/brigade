import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.worktrees import collect
from brigade.system.read_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")
WORKTREE_LIST = (
    "worktree /srv/oak\0HEAD abc1\0branch refs/heads/main\0\0worktree /srv/oak-b12\0HEAD def2\0detached\0locked\0\0"
)


class WorktreesCollectorTest(unittest.TestCase):
    def test_should_list_the_worktrees_of_the_project(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        processes = ScriptedProcesses()
        processes.answer(("git", "worktree", "list", "--porcelain", "-z"), WORKTREE_LIST)
        runtime = create_scripted_runtime(Path(directory.name), processes)
        environment = {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": "{}"}

        # Act
        document = collect(environment, runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "worktrees",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": True,
                "summary": {"worktrees": 2},
                "items": [
                    {"path": "/srv/oak", "branch": "main", "head": "abc1", "detached": False, "locked": False},
                    {"path": "/srv/oak-b12", "branch": None, "head": "def2", "detached": True, "locked": True},
                ],
            },
        )
