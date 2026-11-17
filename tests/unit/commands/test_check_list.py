import argparse
import contextlib
import tempfile
import unittest
from pathlib import Path

from brigade.commands.check_list import COMMAND, check_list
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class CheckListTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        style = root / "shop" / ".brigade" / "checks" / "style"
        style.parent.mkdir(parents=True)
        style.write_text("#!/bin/sh\n")
        style.chmod(0o755)
        self.enterContext(contextlib.chdir(root / "shop"))
        self.runtime = create_test_runtime(create_test_paths(root))

    def test_should_list_the_checks_of_the_project_first(self):
        # Act
        document = check_list(argparse.Namespace(), self.runtime)

        # Assert
        self.assertEqual(document["checks"][0], {"name": "style", "source": "project"})

    def test_should_print_the_name_and_the_source_of_each_check(self):
        # Arrange
        document = {
            "schema_version": 1,
            "checks": [{"name": "style", "source": "project"}, {"name": "acceptance", "source": "built-in"}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "name        source\nstyle       project\nacceptance  built-in")
