import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.git_diff_stat import collect
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")
NUMSTAT = "3\t1\tREADME.md\n10\t0\tsrc/app.py\n"


class GitDiffStatCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def test_should_count_the_lines_changed_between_the_two_refs_it_is_given(self):
        # Arrange
        self.processes.answer(("git", "diff", "--numstat", "--text", "--end-of-options", "v1", "v2", "--"), NUMSTAT)
        environment = {
            "BRIGADE_PROJECT_PATH": "/srv/oak",
            "BRIGADE_SINCE": "2026-10-01",
            "BRIGADE_PARAMS": '{"from": "v1", "to": "v2"}',
        }

        # Act
        document = collect(environment, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "git-diff-stat",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": True,
                "summary": {"files": 2, "insertions": 13, "deletions": 1},
                "items": [
                    {"path": "README.md", "insertions": 3, "deletions": 1},
                    {"path": "src/app.py", "insertions": 10, "deletions": 0},
                ],
            },
        )

    def test_should_count_from_the_main_branch_of_the_project_to_head_by_default(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("MAIN", "main"))}
        )
        self.processes.answer(("git", "diff", "--numstat", "--text", "--end-of-options", "main", "HEAD", "--"), NUMSTAT)
        environment = {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": "{}"}

        # Act
        document = collect(environment, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(document["summary"], {"files": 2, "insertions": 13, "deletions": 1})
