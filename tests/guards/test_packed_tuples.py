import tempfile
import unittest
from pathlib import Path

from tests.guards.find_packed_tuples import find_packed_tuples

TESTS_ROOT = Path(__file__).resolve().parents[1]


class PackedTuplesOfTheTestsTest(unittest.TestCase):
    def test_should_find_no_packed_tuple_compared_in_the_tests(self):
        # Act
        violations = find_packed_tuples(TESTS_ROOT)

        # Assert
        self.assertEqual(violations, [])


class PackedTuplesGuardTest(unittest.TestCase):
    def inspect(self, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "tests" / "unit" / "test_greeter.py"
            module.parent.mkdir(parents=True)
            module.write_text(source)
            return find_packed_tuples(Path(root) / "tests")

    def test_should_flag_a_tuple_literal_compared_by_assert_equal(self):
        # Arrange
        rows = [
            (
                "in a test method",
                (
                    "class GreeterTest:\n    def test_greet(self):\n"
                    "        self.assertEqual((greeting.text, greeting.name), ('Hello', 'Ada'))\n"
                ),
            ),
            (
                "in a helper",
                (
                    "class GreeterTest:\n    def assert_greeted(self):\n"
                    "        self.assertEqual((greeting.text, greeting.name), ('Hello', 'Ada'))\n"
                ),
            ),
        ]
        for case, source in rows:
            with self.subTest(case=case):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, ["tests/unit/test_greeter.py:3 compares a packed tuple"])

    def test_should_let_a_value_the_subject_produced_pass(self):
        # Arrange
        rows = [
            (
                "a text",
                "class GreeterTest:\n    def test_greet(self):\n        self.assertEqual(greeting.text, 'Hello')\n",
            ),
            (
                "a tuple the subject returned",
                "class GreeterTest:\n    def test_greet(self):\n        self.assertEqual(greeting.split(), ('Hello', 'Ada'))\n",
            ),
        ]
        for case, source in rows:
            with self.subTest(case=case):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, [])
