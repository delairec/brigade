import unittest

from brigade.errors import BrigadeError
from brigade.system.split_command import split_command


class SplitCommandTest(unittest.TestCase):
    def test_should_split_the_command_into_the_argv_of_one_call(self):
        # Arrange
        rows = [
            ("ls -1 src", ("ls", "-1", "src")),
            ("printf 'alpha\\nbeta\\n'", ("printf", "alpha\\nbeta\\n")),
            ('grep -c "a b" notes', ("grep", "-c", "a b", "notes")),
            ("echo alpha && echo beta", ("echo", "alpha", "&&", "echo", "beta")),
            ("printf '%s' $HOME > out", ("printf", "%s", "$HOME", ">", "out")),
        ]
        for command, expected in rows:
            with self.subTest(command=command):
                # Act
                argv = split_command(command)

                # Assert
                self.assertEqual(argv, expected)

    def test_should_refuse_naming_a_command_it_cannot_split(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            split_command("printf 'oak")

        # Assert
        self.assertEqual(
            str(refusal.exception), "the command printf 'oak cannot be split into an argv: No closing quotation"
        )
