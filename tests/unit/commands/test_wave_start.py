import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.wave_start import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus
from tests.unit.waves.test_start_project_wave import StartProjectWaveTestCase

NO_PROJECTS = {"PROJECT": {}}


class WaveStartTextTest(unittest.TestCase):
    def test_should_name_the_wave_its_project_its_branch_and_its_tasks(self):
        # Arrange
        document = {
            "schema_version": 1,
            "wave": "tidepool_w16",
            "project": "tidepool",
            "branch": "integration/tidepool_w16",
            "tasks": ["S3", "S6"],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "wave tidepool_w16 of @PROJECT.tidepool on integration/tidepool_w16: S3, S6")


class WaveStartExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveStartRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(project="tidepool", tasks=["S3"])

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveStartOfNamedTasksTest(StartProjectWaveTestCase):
    def test_should_start_the_wave_on_the_tasks_the_command_line_names(self):
        # Arrange
        options = SimpleNamespace(project="shop", tasks=["S10"])

        # Act
        document = COMMAND.run(options, self.runtime)

        # Assert
        self.assertEqual(document["tasks"], ["S10"])


class WaveStartOfAnUnknownProjectTest(unittest.TestCase):
    def test_should_refuse_a_project_not_registered(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        runtime = create_runtime(root, run_process=create_corpus_double(NO_PROJECTS))
        every_startable_task = []

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(project="tidepool", tasks=every_startable_task), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.tidepool is not registered")
