import argparse
import contextlib
import io
import unittest

from brigade.add_command_parsers import add_command_parsers
from brigade.command import Argument, Command


def _run(request, runtime) -> dict:
    return {"schema_version": 1}


def _keep(options):
    return options


def _render(document) -> str:
    return ""


def _decide_done(document) -> int:
    return 0


def _create_command(path: tuple[str, ...], help_text: str, group_help=None, arguments=()) -> Command:
    return Command(
        path=path,
        help=help_text,
        run=_run,
        read_request=_keep,
        render_text=_render,
        decide_exit_code=_decide_done,
        arguments=arguments,
        group_help=group_help,
    )


def _create_common_options() -> argparse.ArgumentParser:
    common_options = argparse.ArgumentParser(add_help=False)
    common_options.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    return common_options


class AddCommandParsersWhenTwoRecordsDeclareOnePathTest(unittest.TestCase):
    def test_should_refuse_naming_the_command_line(self):
        # Arrange
        commands = (
            _create_command(("project", "add"), "register a project", group_help="the projects"),
            _create_command(("project", "add"), "add a project", group_help="the projects"),
        )

        # Act
        with self.assertRaises(ValueError) as raised:
            add_command_parsers(argparse.ArgumentParser(prog="brigade"), commands, _create_common_options())

        # Assert
        self.assertEqual(str(raised.exception), "two command records declare brigade project add")


class AddCommandParsersWhenTwoRecordsDeclareDifferentHelpsForOneGroupTest(unittest.TestCase):
    def test_should_refuse_naming_the_group(self):
        # Arrange
        commands = (
            _create_command(("project", "add"), "register a project", group_help="the projects"),
            _create_command(("project", "list"), "list the projects", group_help="the registered projects"),
        )

        # Act
        with self.assertRaises(ValueError) as raised:
            add_command_parsers(argparse.ArgumentParser(prog="brigade"), commands, _create_common_options())

        # Assert
        self.assertEqual(str(raised.exception), "two command records declare different helps for brigade project")


class AddCommandParsersWhenAGroupHasACommandOfItsOwnTest(unittest.TestCase):
    def test_should_refuse_a_line_declaring_another_help_for_that_group(self):
        # Arrange
        commands = (
            _create_command(("ledger",), "read the event journal"),
            _create_command(("ledger", "budgets"), "the steps per procedure", group_help="the journal"),
        )

        # Act
        with self.assertRaises(ValueError) as raised:
            add_command_parsers(argparse.ArgumentParser(prog="brigade"), commands, _create_common_options())

        # Assert
        self.assertEqual(str(raised.exception), "two command records declare different helps for brigade ledger")

    def test_should_parse_the_group_alone_as_its_own_command(self):
        # Arrange
        ledger = _create_command(("ledger",), "read the event journal")
        budgets = _create_command(("ledger", "budgets"), "the steps per procedure")
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (ledger, budgets), _create_common_options())

        # Act
        options = parser.parse_args(["ledger"])

        # Assert
        self.assertIs(options.command, ledger)

    def test_should_parse_a_line_of_the_group_as_that_line(self):
        # Arrange
        ledger = _create_command(("ledger",), "read the event journal")
        budgets = _create_command(("ledger", "budgets"), "the steps per procedure")
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (ledger, budgets), _create_common_options())

        # Act
        options = parser.parse_args(["ledger", "budgets"])

        # Assert
        self.assertIs(options.command, budgets)


class AddCommandParsersOfAGroupWithNoCommandOfItsOwnTest(unittest.TestCase):
    def test_should_take_the_common_options_before_the_line(self):
        # Arrange
        show = _create_command(
            ("project", "show"), "print a project", group_help="the projects", arguments=(Argument(("name",)),)
        )
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (show,), _create_common_options())

        # Act
        options = parser.parse_args(["project", "--json", "show", "brigade"])

        # Assert
        self.assertEqual(vars(options), {"command": show, "json": True, "name": "brigade"})

    def test_should_refuse_the_group_named_without_its_action(self):
        # Arrange
        show = _create_command(("project", "show"), "print a project", group_help="the projects")
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (show,), _create_common_options())
        errors = io.StringIO()

        # Act
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(errors):
            parser.parse_args(["project"])

        # Assert
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("the following arguments are required: action", errors.getvalue())

    def test_should_parse_no_command_when_none_is_given(self):
        # Arrange
        show = _create_command(("project", "show"), "print a project", group_help="the projects")
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (show,), _create_common_options())

        # Act
        options = parser.parse_args([])

        # Assert
        self.assertIsNone(options.command)
