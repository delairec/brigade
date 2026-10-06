import unittest

from brigade.roles.render_role_file import render_role_file


class RenderRoleFileTest(unittest.TestCase):
    def test_should_write_the_front_matter_between_two_lines_then_the_body(self):
        # Arrange
        front_matter = {"name": "ada", "slot": "plan", "budget": "40"}

        # Act
        text = render_role_file(front_matter, "You are Ada.\n")

        # Assert
        self.assertEqual(text, "---\nname: ada\nslot: plan\nbudget: 40\n---\nYou are Ada.\n")
