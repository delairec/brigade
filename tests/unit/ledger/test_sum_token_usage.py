import unittest

from brigade.ledger.sum_token_usage import sum_token_usage
from brigade.system.token_usage import TokenUsage


class SumTokenUsageTest(unittest.TestCase):
    def test_should_sum_each_count_of_the_usages_reported(self):
        # Arrange
        usages = [
            TokenUsage(input_tokens=1, output_tokens=2, cache_creation_input_tokens=3, cache_read_input_tokens=4),
            None,
            TokenUsage(input_tokens=10, output_tokens=20, cache_creation_input_tokens=30, cache_read_input_tokens=40),
        ]

        # Act
        total = sum_token_usage(usages)

        # Assert
        self.assertEqual(
            total,
            TokenUsage(input_tokens=11, output_tokens=22, cache_creation_input_tokens=33, cache_read_input_tokens=44),
        )

    def test_should_give_none_when_no_usage_is_reported(self):
        # Arrange
        no_usage_reported = [None, None]

        # Act
        total = sum_token_usage(no_usage_reported)

        # Assert
        self.assertIsNone(total)
