import json
import tempfile
import unittest
from pathlib import Path

from brigade.tasks.reserve_task_number import reserve_task_number
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReserveTaskNumberTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_operational_corpus(self.root)
        self.paths = create_test_runtime(create_test_paths(self.root), run_process=ScriptedProcesses()).paths

    def test_should_reserve_the_next_number_of_the_corpus_when_none_is_reserved(self):
        # Act
        number = reserve_task_number(self.paths, "oak", 12)

        # Assert
        self.assertEqual(number, 12)

    def test_should_reserve_past_the_numbers_already_reserved(self):
        # Arrange
        reserve_task_number(self.paths, "oak", 12)

        # Act
        number = reserve_task_number(self.paths, "oak", 12)

        # Assert
        self.assertEqual(number, 13)

    def test_should_reserve_the_next_number_of_the_corpus_once_it_passed_the_reserved_ones(self):
        # Arrange
        reserve_task_number(self.paths, "oak", 12)

        # Act
        number = reserve_task_number(self.paths, "oak", 20)

        # Assert
        self.assertEqual(number, 20)

    def test_should_keep_every_reservation_of_the_project(self):
        # Arrange
        reserve_task_number(self.paths, "oak", 12)

        # Act
        reserve_task_number(self.paths, "oak", 12)

        # Assert
        reservations = self.root / "state" / "reservations" / "oak.json"
        self.assertEqual(
            json.loads(reservations.read_text(encoding="utf-8")), {"schema_version": 1, "task_numbers": [12, 13]}
        )
