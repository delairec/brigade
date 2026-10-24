import unittest

from brigade.corpus.decode_atom import decode_atom

ATOMS_AND_TEXTS = (
    ("escaped regular expression characters", r'"grep \.\(run\|Popen\)("', r"grep \.\(run\|Popen\)("),
    ("an escaped quote", r'"a \"quoted\" word"', 'a "quoted" word'),
    ("an escaped backslash", r'"back \\ slash"', "back \\ slash"),
    ("an escaped backslash before the closing quote", r'"trail\\"', "trail\\"),
    ("a backslash before a letter", r'"line \n kept"', r"line \n kept"),
    ("a reference", "@TASK.B152", "@TASK.B152"),
)


class DecodeAtomTest(unittest.TestCase):
    def test_should_give_the_text_awawa_holds_for_the_atom(self):
        for case, atom, expected_text in ATOMS_AND_TEXTS:
            with self.subTest(case):
                # Act
                text = decode_atom(atom)

                # Assert
                self.assertEqual(text, expected_text)
