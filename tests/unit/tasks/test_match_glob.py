import unittest

from brigade.tasks.match_glob import match_glob


class MatchGlobTest(unittest.TestCase):
    def test_should_tell_whether_the_path_falls_under_the_glob(self):
        # Arrange
        rows = [
            ("a double star crossing directories", "src/cart/**", "src/cart/ui/button.py", True),
            ("a single star within one directory", "src/cart/*", "src/cart/button.py", True),
            ("a single star stopping at a directory", "src/cart/*", "src/cart/ui/button.py", False),
            ("a dot taken literally", "src/*.py", "src/cartxpy", False),
            ("a path outside the glob", "src/cart/**", "src/billing/charge.py", False),
        ]
        for case, glob, path, expected in rows:
            with self.subTest(case=case):
                # Act
                matched = match_glob(glob, path)

                # Assert
                self.assertEqual(matched, expected)
