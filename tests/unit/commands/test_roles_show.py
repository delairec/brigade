import argparse
import contextlib
import io
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.add_command_parsers import add_command_parsers
from brigade.commands.roles_show import COMMAND
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

AUDITOR_ROLE = """---
name: auditor
slot: review
work: reviews a pull request
reasoning: deep
capabilities: read
budget: 30
returns: the findings
---
You review the pull request.
Report every finding.
"""
AUDITOR_FRONT_MATTER = {
    "name": "auditor",
    "slot": "review",
    "work": "reviews a pull request",
    "reasoning": "deep",
    "capabilities": "read",
    "budget": "30",
    "returns": "the findings",
}


class RolesShowTextTest(unittest.TestCase):
    def test_should_print_the_role_file_whole(self):
        # Arrange
        document = {
            "schema_version": 1,
            "slot": "review",
            "role": "auditor",
            "source": "machine",
            "front_matter": {"name": "auditor", "slot": "review"},
            "body": "You review the pull request.\n",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "---\nname: auditor\nslot: review\n---\nYou review the pull request.")

    def test_should_print_the_front_matter_and_the_size_of_the_body(self):
        # Arrange
        document = {
            "schema_version": 1,
            "slot": "review",
            "role": "auditor",
            "source": "machine",
            "front_matter": {"name": "auditor", "slot": "review"},
            "body_lines": 2,
            "body_bytes": 51,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "---\nname: auditor\nslot: review\n---\nbody: 2 lines, 51 bytes, source machine")


class RolesShowExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class RolesShowRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(slot="review", short=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RolesShowArgumentsTest(unittest.TestCase):
    def test_should_refuse_a_slot_outside_the_nine(self):
        # Arrange
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (COMMAND,), argparse.ArgumentParser(add_help=False))
        errors = io.StringIO()

        # Act
        with self.assertRaises(SystemExit) as refusal, contextlib.redirect_stderr(errors):
            parser.parse_args(["roles", "show", "cook"])

        # Assert
        self.assertEqual(refusal.exception.code, 2)
        self.assertIn("invalid choice: 'cook'", errors.getvalue())


class RolesShowOfAMachineRoleTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config" / "roles").mkdir(parents=True)
        (self.root / "config" / "roles" / "auditor.md").write_text(AUDITOR_ROLE, encoding="utf-8")

    def test_should_show_the_role_with_its_body(self):
        # Arrange
        request = Namespace(slot="review", short=False)

        # Act
        document = COMMAND.run(request, create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "slot": "review",
                "role": "auditor",
                "source": "machine",
                "front_matter": AUDITOR_FRONT_MATTER,
                "body": "You review the pull request.\nReport every finding.\n",
            },
        )

    def test_should_show_the_role_with_the_size_of_its_body(self):
        # Arrange
        request = Namespace(slot="review", short=True)

        # Act
        document = COMMAND.run(request, create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "slot": "review",
                "role": "auditor",
                "source": "machine",
                "front_matter": AUDITOR_FRONT_MATTER,
                "body_lines": 2,
                "body_bytes": 51,
            },
        )
