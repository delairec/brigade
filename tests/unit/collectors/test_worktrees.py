import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.worktrees import collect
from brigade.system.parse_configuration import Configuration
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")
WORKTREE_LIST = (
    "worktree /srv/oak\0HEAD abc1\0branch refs/heads/main\0\0worktree /srv/oak-b12\0HEAD def2\0detached\0locked\0\0"
)
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class WorktreesCollectorTest(unittest.TestCase):
    def test_should_list_the_worktrees_of_the_project(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        processes = ScriptedProcesses()
        processes.answer(("git", "worktree", "list", "--porcelain", "-z"), WORKTREE_LIST)
        write_operational_corpus(Path(directory.name))
        runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=processes)
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
