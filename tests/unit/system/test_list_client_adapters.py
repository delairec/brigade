import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.system.list_client_adapters import ClientAdapter, list_client_adapters


class ListClientAdaptersOnAPathWithStrayEntriesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.missing_directory = root / "missing"
        self.search_directory = root / "bin"
        self.search_directory.mkdir()
        unrelated_tool = self.search_directory / "git-credential-helper"
        unrelated_tool.write_text("#!/bin/sh\n")
        unrelated_tool.chmod(0o755)
        local_adapter = self.search_directory / "brigade-client-local"
        local_adapter.write_text("#!/bin/sh\n")
        local_adapter.chmod(0o755)

    def test_should_list_the_adapters_of_the_directories_it_can_read_and_no_other_tool(self):
        # Arrange
        search_path = os.pathsep.join([str(self.missing_directory), str(self.search_directory)])
        runtime = SimpleNamespace(paths=SimpleNamespace(executable_search_path=search_path))

        # Act
        adapters = list_client_adapters(runtime)

        # Assert
        self.assertEqual(
            adapters,
            (
                ClientAdapter(name="local", audience="supported_client"),
                ClientAdapter(name="claude-code", audience="supported_client"),
                ClientAdapter(name="fake", audience="test_suite"),
            ),
        )
