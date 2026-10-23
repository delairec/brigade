import tempfile
import unittest
from pathlib import Path

from tests.guards.find_shared_titles import find_shared_titles

TESTS_ROOT = Path(__file__).resolve().parents[1]
GREETING_TEST = "class GreeterTest(unittest.TestCase):\n    def test_should_greet(self):\n        pass\n"
FAREWELL_TEST = "class GreeterTest(unittest.TestCase):\n    def test_should_say_goodbye(self):\n        pass\n"


class SharedTitlesOfTheTestsTest(unittest.TestCase):
    def test_should_find_no_title_shared_by_the_unit_and_the_cli_suites(self):
        # Act
        violations = find_shared_titles(TESTS_ROOT)

        # Assert
        self.assertEqual(violations, [])


class SharedTitlesGuardTest(unittest.TestCase):
    def inspect(self, unit_source: str, cli_source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            tests_root = Path(root) / "tests"
            for suite, source in [("unit", unit_source), ("cli", cli_source)]:
                module = tests_root / suite / "test_greeter.py"
                module.parent.mkdir(parents=True)
                module.write_text(source)
            return find_shared_titles(tests_root)

    def test_should_flag_a_title_tested_at_both_levels(self):
        # Act
        violations = self.inspect(GREETING_TEST, GREETING_TEST)

        # Assert
        self.assertEqual(violations, ["test_should_greet is tested in tests/unit and in tests/cli"])

    def test_should_leave_titles_proper_to_each_level(self):
        # Act
        violations = self.inspect(GREETING_TEST, FAREWELL_TEST)

        # Assert
        self.assertEqual(violations, [])
