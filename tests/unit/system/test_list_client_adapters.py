import os
import tempfile
import unittest
from pathlib import Path

from brigade.system.list_client_adapters import ClientAdapter, list_client_adapters
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


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
        runtime = create_test_runtime(create_test_paths(Path(self.root.name), executable_search_path=search_path))

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


class ListClientAdaptersOnAPathWithUnfitExecutablesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.search_directory = Path(self.root.name)
        badly_named = self.search_directory / "brigade-client-Local_One"
        badly_named.write_text("#!/bin/sh\n")
        badly_named.chmod(0o755)
        (self.search_directory / "brigade-client-notes").write_text("not executable\n")

    def test_should_list_neither_a_name_off_the_pattern_nor_a_file_it_cannot_run(self):
        # Arrange
        runtime = create_test_runtime(
            create_test_paths(Path(self.root.name), executable_search_path=str(self.search_directory))
        )

        # Act
        adapters = list_client_adapters(runtime)

        # Assert
        self.assertEqual(
            adapters,
            (
                ClientAdapter(name="claude-code", audience="supported_client"),
                ClientAdapter(name="fake", audience="test_suite"),
            ),
        )
