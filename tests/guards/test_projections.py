import tempfile
import unittest
from pathlib import Path

from tests.guards.find_projections import find_projections

TESTS_ROOT = Path(__file__).resolve().parents[1]


class ProjectionsOfTheTestsTest(unittest.TestCase):
    def test_should_find_no_projection_in_the_tests(self):
        # Act
        violations = find_projections(TESTS_ROOT)

        # Assert
        self.assertEqual(violations, [])


class ProjectionsGuardTest(unittest.TestCase):
    def inspect(self, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "tests" / "unit" / "test_greeter.py"
            module.parent.mkdir(parents=True)
            module.write_text(source)
            return find_projections(Path(root) / "tests")

    def test_should_flag_every_comprehension_of_a_test_method(self):
        # Arrange
        rows = [
            ("a list", "    def test_greet(self):\n        names = [call.name for call in calls]\n"),
            ("a set", "    def test_greet(self):\n        names = {call.name for call in calls}\n"),
            ("a mapping", "    def test_greet(self):\n        names = {call.name: call for call in calls}\n"),
            ("a generator", "    def test_greet(self):\n        name = next(call for call in calls)\n"),
        ]
        for case, method in rows:
            with self.subTest(case=case):
                # Act
                violations = self.inspect(f"class GreeterTest:\n{method}")

                # Assert
                self.assertEqual(violations, ["tests/unit/test_greeter.py:3 projects a value in test_greet"])

    def test_should_flag_a_sorted_value_compared_by_assert_equal(self):
        # Arrange
        source = "class GreeterTest:\n    def test_greet(self):\n        self.assertEqual(sorted(names), ['Ada'])\n"

        # Act
        violations = self.inspect(source)

        # Assert
        self.assertEqual(violations, ["tests/unit/test_greeter.py:3 compares a sorted value in test_greet"])

    def test_should_let_a_comprehension_outside_a_test_method_pass(self):
        # Arrange
        rows = [
            (
                "a double",
                "class GreeterDouble:\n    def list_names(self):\n        return [c.name for c in self.calls]\n",
            ),
            ("a module constant", "NAMES = [name.upper() for name in ('ada', 'max')]\n"),
        ]
        for case, source in rows:
            with self.subTest(case=case):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, [])
