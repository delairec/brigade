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
    def inspect(self, source: str, module_name: str = "test_greeter.py") -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "tests" / "unit" / module_name
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

    def test_should_flag_every_comprehension_of_a_function_outside_a_double(self):
        # Arrange
        rows = [
            (
                "a helper method",
                "class GreeterTest:\n    def read_names(self):\n        return [c.name for c in calls]\n",
                "tests/unit/test_greeter.py:3 projects a value in read_names",
            ),
            (
                "an arrangement",
                "class GreeterTest:\n    def setUp(self):\n        self.names = {n: n for n in NAMES}\n",
                "tests/unit/test_greeter.py:3 projects a value in setUp",
            ),
            (
                "a module function",
                "def read_names(calls):\n    return [c.name for c in calls]\n",
                "tests/unit/test_greeter.py:2 projects a value in read_names",
            ),
            (
                "an asynchronous module function",
                "async def read_names(calls):\n    return [c.name for c in calls]\n",
                "tests/unit/test_greeter.py:2 projects a value in read_names",
            ),
            (
                "a function nested in a test method",
                (
                    "class GreeterTest:\n    def test_greet(self):\n        def read_names():\n"
                    "            return [c.name for c in calls]\n"
                ),
                "tests/unit/test_greeter.py:4 projects a value in test_greet",
            ),
        ]
        for case, source, expected_violation in rows:
            with self.subTest(case=case):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_flag_a_sorted_value_compared_in_a_helper_method(self):
        # Arrange
        source = "class GreeterTest:\n    def check_names(self):\n        self.assertEqual(sorted(names), ['Ada'])\n"

        # Act
        violations = self.inspect(source)

        # Assert
        self.assertEqual(violations, ["tests/unit/test_greeter.py:3 compares a sorted value in check_names"])

    def test_should_let_a_comprehension_of_a_double_or_of_a_module_constant_pass(self):
        # Arrange
        rows = [
            (
                "a double",
                "class GreeterDouble:\n    def list_names(self):\n        return [c.name for c in self.calls]\n",
            ),
            (
                "a double declared in a function",
                (
                    "def create_greeter():\n    class GreeterDouble:\n        def list_names(self):\n"
                    "            return [c.name for c in self.calls]\n    return GreeterDouble()\n"
                ),
            ),
            ("a module constant", "NAMES = [name.upper() for name in ('ada', 'max')]\n"),
        ]
        for case, source in rows:
            with self.subTest(case=case):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, [])

    def test_should_let_a_function_of_a_module_that_is_not_a_test_module_pass(self):
        # Arrange
        source = "def read_names(calls):\n    return [c.name for c in calls]\n"

        # Act
        violations = self.inspect(source, "greeter_support.py")

        # Assert
        self.assertEqual(violations, [])
