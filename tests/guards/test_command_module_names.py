import unittest

from tests.guards.find_misnamed_command_modules import find_misnamed_command_modules


class CommandModuleNamesOfThePackageTest(unittest.TestCase):
    def test_should_find_every_command_module_named_after_its_command_line(self):
        # Act
        misnamings = find_misnamed_command_modules("brigade.commands")

        # Assert
        self.assertEqual(misnamings, [])


class CommandModuleNamesGuardTest(unittest.TestCase):
    def test_should_flag_a_module_named_after_another_command_line(self):
        # Act
        misnamings = find_misnamed_command_modules("tests.guards.fixtures.command_modules")

        # Assert
        self.assertEqual(
            misnamings,
            [
                "tests.guards.fixtures.command_modules.awawa declares brigade corpus",
                "tests.guards.fixtures.command_modules.runs_stop declares brigade runs list",
            ],
        )
