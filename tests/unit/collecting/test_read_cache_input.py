import tempfile
import unittest
from pathlib import Path

from brigade.collecting.read_cache_input import read_cache_input
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadCacheInputTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)

    def test_should_key_a_repository_collector_on_the_commit_of_head(self):
        # Arrange
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="c0ffee\n"
        )

        # Act
        cache_input = read_cache_input("git-log", Path("/srv/oak"), self.runtime)

        # Assert
        self.assertEqual(cache_input, "c0ffee")

    def test_should_key_the_ledger_collector_on_the_size_of_the_month_files(self):
        # Arrange
        ledger = self.root / "state" / "ledger"
        ledger.mkdir(parents=True)
        (ledger / "2026-09.jsonl").write_text("12345\n", encoding="utf-8")
        (ledger / "2026-10.jsonl").write_text("1234\n", encoding="utf-8")
        (ledger / "notes.txt").write_text("not a month of the ledger\n", encoding="utf-8")

        # Act
        cache_input = read_cache_input("ledger", Path("/srv/oak"), self.runtime)

        # Assert
        self.assertEqual(cache_input, 11)

    def test_should_key_any_other_collector_on_nothing(self):
        # Act
        cache_input = read_cache_input("weather", Path("/srv/oak"), self.runtime)

        # Assert
        self.assertIsNone(cache_input)
