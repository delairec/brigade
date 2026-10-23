import tempfile
import unittest
from pathlib import Path

from tests.guards.find_misnamed_doubles import find_misnamed_doubles

TESTS_ROOT = Path(__file__).resolve().parents[1]


class DoubleNamesOfTheTestsTest(unittest.TestCase):
    def test_should_find_no_class_of_a_test_module_missing_the_double_suffix(self):
        # Act
        violations = find_misnamed_doubles(TESTS_ROOT)

        # Assert
        self.assertEqual(violations, [])


class DoubleNamesGuardTest(unittest.TestCase):
    def inspect(self, module_name: str, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "tests" / module_name
            module.parent.mkdir()
            module.write_text(source)
            return find_misnamed_doubles(Path(root) / "tests")

    def test_should_let_a_test_a_test_case_and_a_double_pass(self):
        for case, source in [
            ("a test", "class GreeterTest(unittest.TestCase):\n    pass\n"),
            ("a test case", "class GreeterTestCase(unittest.TestCase):\n    pass\n"),
            ("a double", "class ClockDouble:\n    pass\n"),
        ]:
            with self.subTest(case=case):
                # Act
                violations = self.inspect("test_greeter.py", source)

                # Assert
                self.assertEqual(violations, [])

    def test_should_flag_a_class_of_a_test_module_missing_the_double_suffix(self):
        # Arrange
        source = "class GreeterTest(unittest.TestCase):\n    pass\n\n\nclass ScriptedPoller:\n    pass\n"

        # Act
        violations = self.inspect("test_greeter.py", source)

        # Assert
        self.assertEqual(violations, ["tests/test_greeter.py:5 ScriptedPoller lacks the Double suffix"])

    def test_should_flag_a_shared_set_up_named_as_an_arrangement(self):
        # Arrange
        source = "class GreeterArrangement:\n    pass\n"

        # Act
        violations = self.inspect("test_greeter.py", source)

        # Assert
        self.assertEqual(violations, ["tests/test_greeter.py:1 GreeterArrangement lacks the Double suffix"])

    def test_should_leave_a_helper_module_of_the_tests(self):
        # Arrange
        source = "class TemporaryMachine:\n    pass\n"

        # Act
        violations = self.inspect("temporary_machine.py", source)

        # Assert
        self.assertEqual(violations, [])
