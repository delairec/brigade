import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.git_log import collect
from brigade.system.parse_configuration import Configuration
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")
LOG = (
    "\x1eabc1\x1fAda\x1f1760000000\x1fadd the parser\n\nREADME.md\nsrc/parse.py\n"
    "\x1edef2\x1fBob\x1f1760003600\x1ffix the parser\n\nsrc/parse.py\n"
)
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class GitLogCollectorTest(unittest.TestCase):
    def test_should_list_the_commits_since_the_start_with_the_files_they_touched(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        processes = ScriptedProcesses()
        processes.answer(
            (
                "git",
                "log",
                "--since=2026-10-01 00:00:00 +0000",
                "--format=%x1e%H%x1f%an%x1f%at%x1f%s",
                "--name-only",
                "HEAD",
                "--",
            ),
            LOG,
        )
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
                "collector": "git-log",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": True,
                "summary": {"commits": 2, "files": 2},
                "items": [
                    {
                        "sha": "abc1",
                        "author": "Ada",
                        "date": "2025-10-09T08:53:20Z",
                        "subject": "add the parser",
                        "files": ["README.md", "src/parse.py"],
                    },
                    {
                        "sha": "def2",
                        "author": "Bob",
                        "date": "2025-10-09T09:53:20Z",
                        "subject": "fix the parser",
                        "files": ["src/parse.py"],
                    },
                ],
            },
        )
