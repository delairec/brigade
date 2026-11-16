import unittest

from brigade.git.map_cited_lines import map_cited_lines

UNCHANGED = ""
CHANGED_LINES = None


class MapCitedLinesTest(unittest.TestCase):
    def test_should_tell_where_the_cited_lines_stand_after_the_diff(self):
        rows = (
            ("a file the diff does not touch", UNCHANGED, (3, 4)),
            ("two lines inserted above", "@@ -1,0 +2,2 @@\n+one\n+two\n", (5, 6)),
            ("two lines removed above", "@@ -1,2 +0,0 @@\n-one\n-two\n", (1, 2)),
            ("one line replaced by two above", "@@ -2 +2,2 @@\n-one\n+two\n+three\n", (4, 5)),
            ("a line inserted between the cited lines", "@@ -3,0 +4 @@\n+one\n", CHANGED_LINES),
            ("a line inserted right below", "@@ -4,0 +5 @@\n+one\n", (3, 4)),
            ("a cited line replaced", "@@ -4 +4 @@\n-one\n+two\n", CHANGED_LINES),
            ("a line replaced below", "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -9 +9,3 @@\n-one\n+two\n", (3, 4)),
        )
        for case, diff, expected in rows:
            with self.subTest(case):
                # Act
                lines = map_cited_lines(diff, 3, 4)

                # Assert
                self.assertEqual(lines, expected)
