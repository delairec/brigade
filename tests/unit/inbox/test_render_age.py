import unittest

from brigade.inbox.render_age import render_age


class RenderAgeTest(unittest.TestCase):
    def test_should_render_the_age_in_its_largest_whole_unit(self):
        # Arrange
        rows = [
            ("under a minute", 59, "59s"),
            ("a minute", 60, "1m"),
            ("under an hour", 3599, "59m"),
            ("an hour", 3600, "1h"),
            ("under a day", 86399, "23h"),
            ("a day", 86400, "1d"),
            ("ten days", 900000, "10d"),
        ]
        for case, age_s, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = render_age(age_s)

                # Assert
                self.assertEqual(text, expected_text)
