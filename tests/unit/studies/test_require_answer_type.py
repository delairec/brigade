import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.require_answer_type import require_answer_type
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class RequireAnswerTypeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)

    def test_should_accept_a_type_the_schema_declares(self):
        # Arrange
        self.processes.answer(("awawa", "show", "FINDING", "/srv/corpus"), stdout="SCHEMA FINDING\n")

        # Act
        required = require_answer_type(self.runtime, Path("/srv/corpus"), "FINDING")

        # Assert
        self.assertIsNone(required)

    def test_should_refuse_a_type_the_schema_does_not_declare(self):
        # Arrange
        self.processes.answer(("awawa", "show", "VERDICT", "/srv/corpus"), exit_code=1)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            require_answer_type(self.runtime, Path("/srv/corpus"), "VERDICT")

        # Assert
        self.assertEqual(str(refusal.exception), "the schema of the operational corpus declares no VERDICT")
