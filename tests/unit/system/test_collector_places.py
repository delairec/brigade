import unittest
from pathlib import Path

from brigade.system.collector_places import CollectorPlaces, locate_collectors
from tests.unit.create_test_runtime import create_test_paths


class LocateCollectorsTest(unittest.TestCase):
    def test_should_place_the_collectors_of_the_project_of_the_machine_and_of_path(self):
        # Act
        places = locate_collectors(Path("/srv/shop"), create_test_paths(Path("/home/ada")))

        # Assert
        self.assertEqual(
            places,
            CollectorPlaces(
                project_directory=Path("/srv/shop/.brigade/collectors"),
                machine_directory=Path("/home/ada/config/brigade/collectors"),
                executable_search_path="/usr/bin",
            ),
        )
