import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.waves.read_wave_request import read_wave_request
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadWaveRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def test_should_read_the_request_from_the_operational_corpus(self):
        # Arrange
        self.processes.answer_entity(self.runtime.paths.config_root, "REQUEST", "oak_1", (("STATUS", "planning"),))

        # Act
        request = read_wave_request(self.runtime, "oak_1")

        # Assert
        self.assertEqual(request, Entity(name="oak_1", fields=(EntityField(name="STATUS", value="planning"),)))

    def test_should_refuse_a_request_the_operational_corpus_does_not_define(self):
        # Arrange
        root = str(self.runtime.paths.config_root)
        self.processes.answer(
            ("awawa", "show", "@REQUEST.oak_9", "--json", root),
            exit_code=1,
            stderr="awawa show: @REQUEST.oak_9 is not defined in the workspace\n",
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_wave_request(self.runtime, "oak_9")

        # Assert
        self.assertEqual(str(refusal.exception), "@REQUEST.oak_9 is not defined in the operational corpus")

    def test_should_refuse_to_read_a_request_before_the_operational_corpus_exists(self):
        # Arrange
        self.runtime.paths.schema_file.unlink()

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_wave_request(self.runtime, "oak_1")

        # Assert
        self.assertEqual(str(refusal.exception), "the operational corpus is missing; run brigade init first")
