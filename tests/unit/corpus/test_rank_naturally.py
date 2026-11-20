import unittest

from brigade.corpus.rank_naturally import rank_naturally


class RankNaturallyTest(unittest.TestCase):
    def test_should_rank_the_numbers_of_two_names_by_value_case_aside(self):
        # Act
        lower_two = rank_naturally("b2")

        # Assert
        self.assertLess(lower_two, rank_naturally("B10"))
