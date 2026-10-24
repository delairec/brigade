import unittest

from brigade.git.list_added_lines import AddedLine
from brigade.verify.check_privacy import PrivacyPatterns, check_privacy


class CheckPrivacyTest(unittest.TestCase):
    def test_should_fail_each_added_line_holding_private_data_but_what_the_public_patterns_allow(self):
        # Arrange
        patterns = PrivacyPatterns(private=(r"ACME-\d+",), public=(r"noreply@example\.org",))
        added_lines = (
            AddedLine(path="README.md", line=3, text="write to ada@corp.io"),
            AddedLine(path="README.md", line=4, text="see /home/ada/notes"),
            AddedLine(path="docs/a.md", line=1, text="ticket ACME-12"),
            AddedLine(path="docs/a.md", line=2, text="by noreply@example.org"),
        )

        # Act
        check = check_privacy(patterns, added_lines)

        # Assert
        self.assertEqual(
            check,
            {
                "name": "privacy",
                "verdict": "fail",
                "findings": [
                    "README.md:3: an e-mail address",
                    "README.md:4: a home path",
                    r"docs/a.md:1: the PRIVATE pattern ACME-\d+",
                ],
            },
        )

    def test_should_fail_a_match_that_a_public_pattern_covers_only_in_part(self):
        # Arrange
        patterns = PrivacyPatterns(private=(), public=("/home/alice",))
        added_lines = (AddedLine(path="src/notes.py", line=4, text="ARCHIVE = '/home/alice.old/shop'"),)

        # Act
        check = check_privacy(patterns, added_lines)

        # Assert
        self.assertEqual(check, {"name": "privacy", "verdict": "fail", "findings": ["src/notes.py:4: a home path"]})
