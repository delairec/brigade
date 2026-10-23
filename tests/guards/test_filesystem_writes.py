import tempfile
import unittest
from pathlib import Path

from tests.guards.find_filesystem_writes import find_filesystem_writes

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class FilesystemWritesOfThePackageTest(unittest.TestCase):
    def test_should_find_no_write_to_the_filesystem_outside_the_system_package(self):
        # Act
        violations = find_filesystem_writes(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class FilesystemWritesGuardTest(unittest.TestCase):
    def test_should_flag_a_write_to_the_filesystem_outside_the_system_package(self):
        # Arrange
        rows = [
            ("open(path, 'w')\n", "brigade/runs/journal.py:1 writes through open"),
            ("open(path, mode='a', encoding='utf-8')\n", "brigade/runs/journal.py:1 writes through open"),
            ("path.open('x')\n", "brigade/runs/journal.py:1 writes through open"),
            ("path.open('r+')\n", "brigade/runs/journal.py:1 writes through open"),
            ("path.write_text(text)\n", "brigade/runs/journal.py:1 writes through write_text"),
            ("path.write_bytes(content)\n", "brigade/runs/journal.py:1 writes through write_bytes"),
            ("path.mkdir(parents=True)\n", "brigade/runs/journal.py:1 writes through mkdir"),
            ("staged.replace(target)\n", "brigade/runs/journal.py:1 writes through replace"),
            ("staged.rename(target)\n", "brigade/runs/journal.py:1 writes through rename"),
            ("import os\nos.rename(source, target)\n", "brigade/runs/journal.py:2 writes through os.rename"),
            ("import os\nos.replace(source, target)\n", "brigade/runs/journal.py:2 writes through os.replace"),
            ("import shutil\nshutil.rmtree(tree)\n", "brigade/runs/journal.py:2 writes through shutil.rmtree"),
            ("from shutil import rmtree\nrmtree(tree)\n", "brigade/runs/journal.py:2 writes through shutil.rmtree"),
            (
                "import tempfile\ntempfile.mkdtemp(dir=root)\n",
                "brigade/runs/journal.py:2 writes through tempfile.mkdtemp",
            ),
        ]
        for source, expected_violation in rows:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / "brigade" / "runs" / "journal.py"
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_filesystem_writes(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_let_a_read_and_a_text_replacement_through_anywhere(self):
        # Arrange
        rows = [
            "open(path)\n",
            "open(path, 'rb')\n",
            "path.open(encoding='utf-8')\n",
            "text.replace('a', 'b')\n",
            "moment.replace(tzinfo=UTC)\n",
            "replace(record, state='done')\n",
        ]
        for source in rows:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / "brigade" / "runs" / "journal.py"
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_filesystem_writes(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [])

    def test_should_let_the_system_package_write(self):
        # Arrange
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "brigade" / "system" / "write_text_file.py"
            module.parent.mkdir(parents=True)
            module.write_text("path.write_text(text)\nimport shutil\nshutil.rmtree(tree)\n")

            # Act
            violations = find_filesystem_writes(Path(root) / "brigade")

            # Assert
            self.assertEqual(violations, [])
