import argparse
import contextlib
import io
import unittest

from brigade.add_command_parsers import add_command_parsers
from brigade.command import Argument, Command, ExclusiveArguments


def _run(request, runtime) -> dict:
    return {"schema_version": 1}


def _keep(options):
    return options


def _render(document) -> str:
    return ""


def _decide_done(document) -> int:
    return 0


def _create_command(
    path: tuple[str, ...], help_text: str, group_help=None, arguments=(), render_passed_stderr=None
) -> Command:
    return Command(
        path=path,
        help=help_text,
        run=_run,
        read_request=_keep,
        render_text=_render,
        decide_exit_code=_decide_done,
        arguments=arguments,
        group_help=group_help,
        render_passed_stderr=render_passed_stderr,
    )


def _capture_refusal(parser: argparse.ArgumentParser, arguments: list[str]) -> tuple[int, str]:
    errors = io.StringIO()
    with unittest.TestCase().assertRaises(SystemExit) as raised, contextlib.redirect_stderr(errors):
        parser.parse_args(arguments)
    return raised.exception.code, errors.getvalue()


def _print_help(parser: argparse.ArgumentParser, arguments: list[str]) -> str:
    page = io.StringIO()
    with contextlib.suppress(SystemExit), contextlib.redirect_stdout(page):
        parser.parse_args(arguments)
    return page.getvalue()


def _create_common_options() -> argparse.ArgumentParser:
    common_options = argparse.ArgumentParser(add_help=False)
    common_options.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    return common_options


class AddCommandParsersOfAGroupDeclaredByTheRecordsOfItsLinesTest(unittest.TestCase):
    def test_should_list_the_group_with_the_help_its_lines_declare(self):
        # Arrange
        show = _create_command(("project", "show"), "print a project", group_help="the registered projects")
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (show,), _create_common_options())

        # Act
        help_text = parser.format_help()

        # Assert
        self.assertIn("the registered projects", help_text)


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

        # Act
        exit_code, errors = _capture_refusal(parser, ["project"])

        # Assert
        self.assertEqual(exit_code, 2)
        self.assertIn("the following arguments are required: action", errors)

    def test_should_parse_no_command_when_none_is_given(self):
        # Arrange
        show = _create_command(("project", "show"), "print a project", group_help="the projects")
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (show,), _create_common_options())

        # Act
        options = parser.parse_args([])

        # Assert
        self.assertIsNone(options.command)


class AddCommandParsersOfAPassthroughRecordTest(unittest.TestCase):
    def test_should_print_its_help_under_the_options_of_its_path(self):
        # Arrange
        tool = _create_command(("tool",), "read the tool's tree")
        passthrough = _create_command(("tool",), "-- <tool args>: run the tool there", render_passed_stderr=_render)
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (tool, passthrough), _create_common_options())

        # Act
        page = _print_help(parser, ["tool", "--help"])

        # Assert
        self.assertRegex(page, r"\noptions:\n(?:.+\n)+\n-- <tool args>: run the tool there\n\Z")

    def test_should_leave_the_command_record_of_its_path_parsing_that_path(self):
        # Arrange
        tool = _create_command(("tool",), "read the tool's tree")
        passthrough = _create_command(("tool",), "-- <tool args>: run the tool there", render_passed_stderr=_render)
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (passthrough, tool), _create_common_options())

        # Act
        options = parser.parse_args(["tool"])

        # Assert
        self.assertIs(options.command, tool)


class AddCommandParsersWhenAPassthroughRecordHasNoCommandRecordOnItsPathTest(unittest.TestCase):
    def test_should_refuse_naming_the_command_line(self):
        # Arrange
        passthrough = _create_command(("tool",), "-- <tool args>: run the tool there", render_passed_stderr=_render)

        # Act
        with self.assertRaises(ValueError) as raised:
            add_command_parsers(argparse.ArgumentParser(prog="brigade"), (passthrough,), _create_common_options())

        # Assert
        self.assertEqual(
            str(raised.exception), "a passthrough record declares brigade tool, which no command record declares"
        )


class AddCommandParsersWhenTwoPassthroughRecordsDeclareOnePathTest(unittest.TestCase):
    def test_should_refuse_naming_the_command_line(self):
        # Arrange
        commands = (
            _create_command(("tool",), "read the tool's tree"),
            _create_command(("tool",), "-- <tool args>: run the tool there", render_passed_stderr=_render),
            _create_command(("tool",), "-- <tool args>: pass the tool", render_passed_stderr=_render),
        )

        # Act
        with self.assertRaises(ValueError) as raised:
            add_command_parsers(argparse.ArgumentParser(prog="brigade"), commands, _create_common_options())

        # Assert
        self.assertEqual(str(raised.exception), "two passthrough records declare brigade tool")


class AddCommandParsersWithExclusiveArgumentsTest(unittest.TestCase):
    def test_should_refuse_two_arguments_of_an_exclusive_group_together(self):
        # Arrange
        command = Command(
            path=("runs", "show"),
            help="show a run",
            run=print,
            read_request=vars,
            render_text=str,
            decide_exit_code=len,
            arguments=(
                ExclusiveArguments(
                    arguments=(
                        Argument(("--all",), {"action": "store_true"}),
                        Argument(("--last",), {"action": "store_true"}),
                    )
                ),
            ),
        )
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, [command], argparse.ArgumentParser(add_help=False))

        # Act
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
            parser.parse_args(["runs", "show", "--all", "--last"])

        # Assert
        self.assertEqual(exit_.exception.code, 2)
