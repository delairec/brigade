import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.system.collector_places import CollectorPlaces
from brigade.system.list_collectors import list_collectors


def write_file(path: Path, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(mode)


class ListCollectorsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        write_file(self.root / "shop" / "coverage", 0o755)
        write_file(self.root / "shop" / "README.md", 0o644)
        write_file(self.root / "bin" / "brigade-collector-latency", 0o755)
        write_file(self.root / "bin" / "awawa", 0o755)
        self.places = CollectorPlaces(
            project_directory=self.root / "shop",
            machine_directory=self.root / "no-machine-collectors",
            executable_search_path=f"{self.root / 'bin'}:{self.root / 'missing'}",
        )

    def test_should_list_the_executables_of_the_project_the_machine_and_path(self):
        # Act
        collectors = list_collectors(self.places)

        # Assert
        self.assertEqual(
            [collector for collector in collectors if collector["source"] != "built-in"],
            [{"name": "coverage", "source": "project"}, {"name": "latency", "source": "PATH"}],
        )

    def test_should_list_the_built_ins_by_their_dashed_names(self):
        # Act
        collectors = list_collectors(self.places)

        # Assert
        self.assertIn({"name": "pr-list", "source": "built-in"}, collectors)
