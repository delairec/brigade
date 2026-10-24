import unittest

from tests.value_matchers import DurationUnderMatcher, PatternMatcher

UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
LIMIT_MS = 10000


class PatternMatcherTest(unittest.TestCase):
    def test_should_equal_only_a_text_matching_its_whole_pattern(self):
        for case, value, expected in [
            ("a generated session", "6a24d4f9-8991-49e5-8cca-8683c79dff59", True),
            ("a session the client named", "rate-limited-session", False),
            ("a session followed by more text", "6a24d4f9-8991-49e5-8cca-8683c79dff59 and more", False),
            ("no session", None, False),
        ]:
            with self.subTest(case=case):
                # Act
                matched = PatternMatcher(UUID_PATTERN) == value

                # Assert
                self.assertIs(matched, expected)


class DurationUnderMatcherTest(unittest.TestCase):
    def test_should_equal_only_a_duration_from_zero_up_to_its_limit_excluded(self):
        for case, value, expected in [
            ("no time measured", 0, True),
            ("just under the limit", 9999, True),
            ("at the limit", 10000, False),
            ("a negative duration", -1, False),
            ("a duration given as text", "402", False),
        ]:
            with self.subTest(case=case):
                # Act
                matched = DurationUnderMatcher(LIMIT_MS) == value

                # Assert
                self.assertIs(matched, expected)
