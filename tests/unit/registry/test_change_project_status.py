import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.registry.change_project_status import change_project_status
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

ACTIVE_SHOP = 'PROJECT shop\n\tPATH "/srv/shop"\n\tSTATUS active\n'


class ChangeProjectStatusTestCase(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.registry = self.paths.config_root / "projects.awawa"

    def create_awawa(self, status: str) -> RecordingProcessRunner:
        config_root = str(self.paths.config_root)
        shown = {"fields": [{"name": "PATH", "atoms": ['"/srv/shop"']}, {"name": "STATUS", "atoms": [status]}]}
        return RecordingProcessRunner(
            {
                ("awawa", "status", "PROJECT", "--json", config_root): ProcessAnswer(
                    stdout=json.dumps({"entities": [{"type": "PROJECT", "name": "shop"}]})
                ),
                ("awawa", "show", "@PROJECT.shop", "--json", config_root): ProcessAnswer(stdout=json.dumps(shown)),
            }
        )


class ChangeProjectStatusOfAnActiveProjectTest(ChangeProjectStatusTestCase):
    def test_should_pause_the_project_in_the_registry(self):
        # Arrange
        self.registry.write_text(ACTIVE_SHOP)
        runtime = create_test_runtime(self.paths, run_process=self.create_awawa("active"))

        # Act
        document = change_project_status(runtime, "shop", "paused")

        # Assert
        self.assertEqual(document, {"schema_version": 1, "project": "shop", "status": "paused", "changed": True})
        self.assertEqual(self.registry.read_text(), 'PROJECT shop\n\tPATH "/srv/shop"\n\tSTATUS paused\n')


class ChangeProjectStatusAlreadySetTest(ChangeProjectStatusTestCase):
    def test_should_leave_the_registry_unchanged(self):
        # Arrange
        self.registry.write_text(ACTIVE_SHOP)
        runtime = create_test_runtime(self.paths, run_process=self.create_awawa("active"))

        # Act
        document = change_project_status(runtime, "shop", "active")

        # Assert
        self.assertEqual(document, {"schema_version": 1, "project": "shop", "status": "active", "changed": False})
        self.assertEqual(self.registry.read_text(), ACTIVE_SHOP)


class ChangeProjectStatusOfAProjectTheFileDoesNotWriteTest(ChangeProjectStatusTestCase):
    def test_should_refuse_naming_the_registry_file(self):
        # Arrange
        self.registry.write_text('PROJECT tidepool\n\tPATH "/srv/tidepool"\n')
        runtime = create_test_runtime(self.paths, run_process=self.create_awawa("active"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            change_project_status(runtime, "shop", "paused")

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.shop is not written in projects.awawa")
