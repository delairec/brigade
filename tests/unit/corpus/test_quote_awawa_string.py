import unittest

from brigade.corpus.quote_awawa_string import quote_awawa_string


class QuoteAwawaStringTest(unittest.TestCase):
    def test_should_quote_the_value_escaping_backslashes_and_quotes(self):
        # Act
        quoted = quote_awawa_string('C:\\shop "main"')

        # Assert
        self.assertEqual(quoted, '"C:\\\\shop \\"main\\""')
