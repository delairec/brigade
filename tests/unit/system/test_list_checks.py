import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.system.check_places import CheckPlaces
from brigade.system.list_checks import list_checks
from tests.unit.system.test_list_collectors import write_file


class ListChecksTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def test_should_list_the_checks_of_the_project_the_machine_and_path_first(self):
        # Arrange
        write_file(self.root / "shop" / "style", 0o755)
        write_file(self.root / "shop" / "README.md", 0o644)
        write_file(self.root / "config" / "latency", 0o755)
        write_file(self.root / "bin" / "brigade-check-coverage", 0o755)
        write_file(self.root / "bin" / "awawa", 0o755)
        places = CheckPlaces(
            project_directory=self.root / "shop",
            machine_directory=self.root / "config",
            executable_search_path=f"{self.root / 'bin'}:{self.root / 'missing'}",
        )

        # Act
        checks = list_checks(places)

        # Assert
        self.assertEqual(
            checks[:3],
            [
                {"name": "style", "source": "project"},
                {"name": "latency", "source": "machine"},
                {"name": "coverage", "source": "PATH"},
            ],
        )

    def test_should_list_the_checks_of_the_pull_request_the_draft_and_the_forge_logins_as_built_ins(self):
        # Arrange
        places = CheckPlaces(
            project_directory=self.root / "no-project-checks",
            machine_directory=self.root / "no-machine-checks",
            executable_search_path="",
        )

        # Act
        checks = list_checks(places)

        # Assert
        self.assertEqual(
            checks,
            [
                {"name": "acceptance", "source": "built-in"},
                {"name": "ancestry", "source": "built-in"},
                {"name": "body", "source": "built-in"},
                {"name": "check_runs", "source": "built-in"},
                {"name": "corpus_at_head", "source": "built-in"},
                {"name": "forge_logins", "source": "built-in"},
                {"name": "moved_citations", "source": "built-in"},
                {"name": "overlapping_deliverables", "source": "built-in"},
                {"name": "privacy", "source": "built-in"},
                {"name": "promotion", "source": "built-in"},
                {"name": "tasks_outside_after", "source": "built-in"},
                {"name": "untouched_files", "source": "built-in"},
            ],
        )
