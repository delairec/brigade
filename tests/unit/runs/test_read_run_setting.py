import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.read_run_setting import read_run_setting
from brigade.system.parse_configuration import Configuration
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadRunSettingTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)

    def test_should_take_the_client_the_registered_project_names(self):
        # Arrange
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        config_root = str(self.paths.config_root)
        awawa = RecordingProcessRunner(
            {
                ("awawa", "status", "PROJECT", "--json", config_root): ProcessAnswer(
                    stdout=json.dumps({"entities": [{"type": "PROJECT", "name": "tidepool"}]})
                ),
                ("awawa", "show", "@PROJECT.tidepool", "--json", config_root): ProcessAnswer(
                    stdout=json.dumps({"fields": [{"name": "CLIENT", "atoms": ['"codex"']}]})
                ),
            }
        )

        # Act
        setting = read_run_setting(
            "tidepool", "build", Configuration(client="claude-code"), create_test_runtime(self.paths, run_process=awawa)
        )

        # Assert
        self.assertEqual(setting.project.name, "tidepool")
        self.assertEqual(setting.client, "codex")

    def test_should_refuse_a_run_no_configuration_names_a_client_for(self):
        # Arrange
        no_project = None

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_run_setting(no_project, "build", Configuration(), create_test_runtime(self.paths))

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"config.toml names no client: set the client key in {self.paths.configuration_file}",
        )
