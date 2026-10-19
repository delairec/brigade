import unittest
from pathlib import Path

from brigade.system.locate_unit_directory import locate_unit_directory
from tests.unit.create_test_runtime import create_test_paths


class LocateUnitDirectoryTest(unittest.TestCase):
    def test_should_place_the_user_units_beside_the_configuration_of_brigade(self):
        # Act
        directory = locate_unit_directory(create_test_paths(Path("/home/ada")))

        # Assert
        self.assertEqual(directory, Path("/home/ada/config/systemd/user"))
