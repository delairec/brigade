import unittest

from tests.guards.list_command_paths import list_command_paths


class ListCommandPathsTest(unittest.TestCase):
    def test_should_list_the_commands_of_brigade_with_their_subcommands(self):
        for kind, path in [
            ("command alone", ("doctor",)),
            ("subcommand", ("runs", "prune")),
            ("subcommand of a command that runs alone too", ("ledger", "compare")),
        ]:
            with self.subTest(kind=kind):
                # Act
                paths = list_command_paths()

                # Assert
                self.assertIn(path, paths)
