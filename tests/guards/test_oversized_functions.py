import tempfile
import unittest
from pathlib import Path

from tests.guards.find_oversized_functions import find_oversized_functions

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"
THIRTY_LINE_FUNCTION = "def decide():\n" + "    step = 1\n" * 28 + "    return step\n"
THIRTY_ONE_LINE_FUNCTION = "def decide():\n" + "    step = 1\n" * 29 + "    return step\n"


class OversizedFunctionsOfTheBrigadePackageTest(unittest.TestCase):
    def test_should_find_no_function_over_thirty_lines_or_four_parameters(self):
        # Act
        violations = find_oversized_functions(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class OversizedFunctionsGuardTest(unittest.TestCase):
    def inspect(self, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "brigade" / "runs" / "plan_run.py"
            module.parent.mkdir(parents=True)
            module.write_text(source)
            return find_oversized_functions(Path(root) / "brigade")

    def test_should_flag_a_function_over_thirty_lines(self):
        # Act
        violations = self.inspect(THIRTY_ONE_LINE_FUNCTION)

        # Assert
        self.assertEqual(violations, ["brigade/runs/plan_run.py:1 decide spans 31 lines, over 30"])

    def test_should_leave_a_function_of_thirty_lines(self):
        # Act
        violations = self.inspect(THIRTY_LINE_FUNCTION)

        # Assert
        self.assertEqual(violations, [])

    def test_should_flag_a_function_over_four_parameters(self):
        # Arrange
        rows = [
            ("def plan(a, b, c, d, e):\n    return a\n", "brigade/runs/plan_run.py:1 plan takes 5 parameters, over 4"),
            ("def plan(a, b, c, *, d, e):\n    return a\n", "brigade/runs/plan_run.py:1 plan takes 5 parameters, over 4"),
            ("def plan(a, b, c, d, *rest):\n    return a\n", "brigade/runs/plan_run.py:1 plan takes 5 parameters, over 4"),
            ("def plan(a, b, c, d, **options):\n    return a\n", "brigade/runs/plan_run.py:1 plan takes 5 parameters, over 4"),
            (
                "class Planner:\n    def plan(self, a, b, c, d, e):\n        return a\n",
                "brigade/runs/plan_run.py:2 plan takes 5 parameters, over 4",
            ),
        ]
        for source, expected_finding in rows:
            with self.subTest(source=source):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, [expected_finding])

    def test_should_leave_four_parameters_beside_the_receiver(self):
        # Arrange
        rows = [
            "def plan(a, b, c, d):\n    return a\n",
            "class Planner:\n    def plan(self, a, b, c, d):\n        return a\n",
            "class Planner:\n    @classmethod\n    def plan(cls, a, b, c, d):\n        return a\n",
        ]
        for source in rows:
            with self.subTest(source=source):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, [])
