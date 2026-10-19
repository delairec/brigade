import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.runs.read_handovers import read_handovers
from tests.unit.create_test_runtime import create_test_paths, create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadHandoversTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)

    def create_runtime(self, policy_fields: list[dict]):
        config_root = str(self.paths.config_root)
        awawa = RecordingProcessRunner(
            {
                ("awawa", "status", "POLICY", "--json", config_root): ProcessAnswer(
                    stdout=json.dumps({"entities": [{"type": "POLICY", "name": "tidepool_policy"}]})
                ),
                ("awawa", "show", "@POLICY.tidepool_policy", "--json", config_root): ProcessAnswer(
                    stdout=json.dumps({"fields": policy_fields})
                ),
            }
        )
        return create_test_runtime(self.paths, run_process=awawa)

    def test_should_allow_two_handovers_to_a_run_without_a_project(self):
        # Arrange
        no_project = None

        # Act
        handovers = read_handovers(create_test_runtime(self.paths), no_project)

        # Assert
        self.assertEqual(handovers, 2)

    def test_should_read_the_handovers_the_policy_of_the_project_sets(self):
        # Arrange
        runtime = self.create_runtime(
            [{"name": "PROJECT", "atoms": ["@PROJECT.tidepool"]}, {"name": "HANDOVERS", "atoms": ["5"]}]
        )

        # Act
        handovers = read_handovers(runtime, "tidepool")

        # Assert
        self.assertEqual(handovers, 5)

    def test_should_allow_two_handovers_when_no_policy_of_the_project_sets_them(self):
        for project, fields in [
            ("tidepool", [{"name": "PROJECT", "atoms": ["@PROJECT.tidepool"]}]),
            ("shop", [{"name": "PROJECT", "atoms": ["@PROJECT.tidepool"]}, {"name": "HANDOVERS", "atoms": ["5"]}]),
        ]:
            with self.subTest(project=project):
                # Act
                handovers = read_handovers(self.create_runtime(fields), project)

                # Assert
                self.assertEqual(handovers, 2)
