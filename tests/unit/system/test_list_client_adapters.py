import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.system.list_client_adapters import _list_directory, _name_executable_adapter, list_client_adapters


class ListDirectoryTest(unittest.TestCase):
    def test_should_return_an_empty_list_when_the_directory_does_not_exist(self):
        # Act
        entries = _list_directory("/nonexistent-directory-xyz")

        # Assert
        self.assertEqual(entries, [])

    def test_should_list_the_entries_of_a_directory(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        (Path(root.name) / "a.txt").touch()
        (Path(root.name) / "b.txt").touch()

        # Act
        entries = _list_directory(root.name)

        # Assert
        self.assertEqual([entry.name for entry in entries], ["a.txt", "b.txt"])


class NameExecutableAdapterTest(unittest.TestCase):
    def test_should_return_none_when_the_name_does_not_start_with_the_prefix(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "other-executable"
        path.touch()
        path.chmod(0o755)

        # Act
        name = _name_executable_adapter(path)

        # Assert
        self.assertIsNone(name)

    def test_should_return_none_when_the_file_is_not_executable(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "brigade-client-test"
        path.touch()
        path.chmod(0o644)

        # Act
        name = _name_executable_adapter(path)

        # Assert
        self.assertIsNone(name)

    def test_should_return_the_name_of_an_executable_adapter(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "brigade-client-test"
        path.touch()
        path.chmod(0o755)

        # Act
        name = _name_executable_adapter(path)

        # Assert
        self.assertEqual(name, "test")


class ListClientAdaptersTest(unittest.TestCase):
    def test_should_list_the_built_in_adapters(self):
        # Arrange
        runtime = mock.Mock()
        runtime.paths.executable_search_path = "/nonexistent"

        # Act
        adapters = list_client_adapters(runtime)

        # Assert
        names = {adapter.name for adapter in adapters}
        self.assertIn("claude-code", names)
        self.assertIn("fake", names)
