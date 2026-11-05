import unittest

from tests.cli.temporary_machine import REPOSITORY_ROOT
from tests.guards.find_unreferenced_commands import find_unreferenced_commands
from tests.guards.list_command_paths import list_command_paths

COMMAND_REFERENCE_PAGE = REPOSITORY_ROOT / "wiki" / "Command-reference.md"


class CommandReferenceTest(unittest.TestCase):
    def test_should_name_every_command_and_subcommand_of_brigade(self):
        # Arrange
        page = COMMAND_REFERENCE_PAGE.read_text(encoding="utf-8")

        # Act
        unreferenced = find_unreferenced_commands(page, list_command_paths())

        # Assert
        self.assertEqual(unreferenced, [])


class CommandReferenceGuardTest(unittest.TestCase):
    def test_should_flag_a_command_no_line_names(self):
        # Arrange
        page_naming_doctor_alone = "| `brigade doctor` | check the prerequisites |\n"

        # Act
        unreferenced = find_unreferenced_commands(page_naming_doctor_alone, [("doctor",), ("serve",)])

        # Assert
        self.assertEqual(unreferenced, ["brigade serve has no line in wiki/Command-reference.md"])

    def test_should_flag_a_subcommand_its_command_line_leaves_out(self):
        # Arrange
        page_naming_two_runs_subcommands = "| `brigade runs list\\|show` | list the runs and prune them |\n"

        # Act
        unreferenced = find_unreferenced_commands(
            page_naming_two_runs_subcommands, [("runs", "list"), ("runs", "prune")]
        )

        # Assert
        self.assertEqual(unreferenced, ["brigade runs prune has no line in wiki/Command-reference.md"])

    def test_should_flag_a_subcommand_named_on_the_line_of_another_command(self):
        # Arrange
        page_naming_show_under_wave_alone = (
            "| `brigade wave show` | print a wave |\n| `brigade runs list` | list the runs |\n"
        )

        # Act
        unreferenced = find_unreferenced_commands(page_naming_show_under_wave_alone, [("runs", "show")])

        # Assert
        self.assertEqual(unreferenced, ["brigade runs show has no line in wiki/Command-reference.md"])

    def test_should_accept_the_forms_of_naming_a_subcommand(self):
        for form, page, path in [
            ("alternatives", "| `brigade wave start\\|requeue` | start the waves |\n", ("wave", "requeue")),
            ("optional", "| `brigade ledger [budgets\\|compare]` | read the journal |\n", ("ledger", "compare")),
            (
                "listed",
                "| `brigade adapter <operation>` | one operation: `probe`, `actions` |\n",
                ("adapter", "actions"),
            ),
        ]:
            with self.subTest(form=form):
                # Act
                unreferenced = find_unreferenced_commands(page, [path])

                # Assert
                self.assertEqual(unreferenced, [])
