import unittest

from brigade.commands.roles_list import COMMAND


class RolesListTextTest(unittest.TestCase):
    def test_should_mark_a_slot_with_no_model_bound_by_a_dash(self):
        # Arrange
        document = {
            "schema_version": 1,
            "client": None,
            "slot_clients": {},
            "roles": [{"slot": "plan", "role": "planner", "source": "built-in", "model": None}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "slot  role     source    model\nplan  planner  built-in  -\nanswers for no client")
