import unittest

from brigade.ledger.sum_reported import sum_reported


class SumReportedTest(unittest.TestCase):
    def test_should_sum_the_values_reported_and_none_when_none_is(self):
        for values, expected in [([3.5, None, 1.25], 4.75), ([None, None], None), ([], None)]:
            with self.subTest(values=values):
                # Act
                total = sum_reported(values)

                # Assert
                self.assertEqual(total, expected)
