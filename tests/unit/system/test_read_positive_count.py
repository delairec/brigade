import argparse
import unittest

from brigade.system.read_positive_count import read_positive_count


class ReadPositiveCountTest(unittest.TestCase):
    def test_should_read_a_count_of_one_or_more(self):
        # Act
        count = read_positive_count("3")

        # Assert
        self.assertEqual(count, 3)

    def test_should_refuse_anything_but_a_count_of_one_or_more(self):
        for text, message in [("0", "'0' is not a count of 1 or more"), ("-2", "'-2' is not a count of 1 or more")]:
            with self.subTest(text=text):
                # Act
                with self.assertRaises(argparse.ArgumentTypeError) as refusal:
                    read_positive_count(text)

                # Assert
                self.assertEqual(str(refusal.exception), message)
