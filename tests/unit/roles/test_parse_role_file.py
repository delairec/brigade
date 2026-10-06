import unittest

from brigade.roles.parse_role_file import RoleFile, RoleFileUnreadable, parse_role_file

ROLE_FILE = (
    "---\n"
    "name: ada\n"
    "slot: plan\n"
    "reasoning: deep\n"
    "capabilities: read, shell\n"
    "budget: 40\n"
    "returns: the wave plan: the tasks, their order\n"
    "---\n"
    "You are Ada.\n"
    "\n"
    "You plan.\n"
)


class ParseRoleFileTest(unittest.TestCase):
    def test_should_read_the_front_matter_and_the_body(self):
        # Act
        role_file = parse_role_file(ROLE_FILE)

        # Assert
        self.assertEqual(
            role_file,
            RoleFile(
                front_matter={
                    "name": "ada",
                    "slot": "plan",
                    "reasoning": "deep",
                    "capabilities": "read, shell",
                    "budget": "40",
                    "returns": "the wave plan: the tasks, their order",
                },
                body="You are Ada.\n\nYou plan.\n",
            ),
        )

    def test_should_refuse_a_file_it_cannot_read_a_front_matter_from(self):
        rows = [
            ("no opening line", "name: ada\n---\nbody\n", "has no front matter between two --- lines"),
            ("no closing line", "---\nname: ada\nbody\n", "has no front matter between two --- lines"),
            ("a line with no key", "---\nname: ada\njust words\n---\nbody\n", "line 3 is not key: value"),
            ("a key declared twice", "---\nname: ada\nname: bilal\n---\nbody\n", "declares name twice"),
        ]
        for case, text, expected_problem in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(RoleFileUnreadable) as raised:
                    parse_role_file(text)

                # Assert
                self.assertEqual(str(raised.exception), expected_problem)
