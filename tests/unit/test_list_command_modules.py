import unittest

from brigade.list_command_modules import list_command_modules


class ListCommandModulesTest(unittest.TestCase):
    def test_should_list_the_command_modules_in_the_order_of_their_names(self):
        # Act
        modules = list_command_modules()

        # Assert
        self.assertEqual(modules[:3], ["adapter_actions", "adapter_launch_argv", "adapter_matrix"])

    def test_should_leave_the_private_modules_out(self):
        # Act
        modules = list_command_modules()

        # Assert
        self.assertNotIn("_read_attribution", modules)
