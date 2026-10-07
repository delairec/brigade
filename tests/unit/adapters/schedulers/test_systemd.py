import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.adapters.schedulers.systemd import read_status
from brigade.errors import ToolNotFound
from brigade.system.run_process import ProcessRecord


def make_runtime(stdout: str = "", exit_code: int = 0, raises: bool = False):
    def run_process(request):
        if raises:
            raise ToolNotFound("systemctl not on PATH")
        return ProcessRecord(argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr="")

    return mock.Mock(run_process=run_process)


class ReadStatusTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.unit_directory = Path(self.root.name) / "units"
        self.unit_directory.mkdir()

    def tearDown(self):
        self.root.cleanup()

    def test_should_report_not_installed_when_no_unit_files_exist(self):
        # Act
        document = read_status({"unit_directory": str(self.unit_directory)}, make_runtime())

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "installed": False,
                "unit_files": [],
                "cron_line": None,
                "next_activation": None,
            },
        )

    def test_should_report_installed_with_the_next_activation(self):
        # Arrange
        (self.unit_directory / "brigade.service").touch()
        (self.unit_directory / "brigade.timer").touch()

        # Act
        document = read_status(
            {"unit_directory": str(self.unit_directory)},
            make_runtime(stdout="1234567890\n"),
        )

        # Assert
        self.assertEqual(document["installed"], True)
        self.assertEqual(document["next_activation"], "1234567890")

    def test_should_report_no_next_activation_when_systemctl_fails(self):
        # Arrange
        (self.unit_directory / "brigade.service").touch()

        # Act
        document = read_status(
            {"unit_directory": str(self.unit_directory)},
            make_runtime(stdout="", exit_code=1),
        )

        # Assert
        self.assertIsNone(document["next_activation"])

    def test_should_report_no_next_activation_when_the_value_is_na(self):
        # Arrange
        (self.unit_directory / "brigade.service").touch()

        # Act
        document = read_status(
            {"unit_directory": str(self.unit_directory)},
            make_runtime(stdout="n/a\n"),
        )

        # Assert
        self.assertIsNone(document["next_activation"])

    def test_should_report_no_next_activation_when_systemctl_is_absent(self):
        # Arrange
        (self.unit_directory / "brigade.service").touch()

        # Act
        document = read_status(
            {"unit_directory": str(self.unit_directory)},
            make_runtime(raises=True),
        )

        # Assert
        self.assertIsNone(document["next_activation"])
