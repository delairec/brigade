import unittest

from brigade.ledger.count_by_name import count_by_name


class CountByNameTest(unittest.TestCase):
    def test_should_count_each_name_in_name_order(self):
        # Act
        counts = count_by_name(["wall_limit", "succeeded", "wall_limit"])

        # Assert
        self.assertEqual(list(counts.items()), [("succeeded", 1), ("wall_limit", 2)])
