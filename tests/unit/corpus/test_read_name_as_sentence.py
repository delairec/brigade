import unittest

from brigade.corpus.read_name_as_sentence import read_name_as_sentence


class ReadNameAsSentenceTest(unittest.TestCase):
    def test_should_read_a_name_as_a_sentence(self):
        for name, sentence in (
            ("TheAwawaTabIsReadOnly", "The awawa tab is read only"),
            ("first_name_given", "first name given"),
            ("ReadsJSONFiles", "Reads JSON files"),
            ("MAX_FACTS", "MAX FACTS"),
            ("LeTagM18Reached", "Le tag M18 reached"),
            ("B273", "B273"),
            ("_private_name", "private name"),
        ):
            with self.subTest(name=name):
                # Act
                read = read_name_as_sentence(name)

                # Assert
                self.assertEqual(read, sentence)
