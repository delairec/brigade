import tempfile
import unittest
from pathlib import Path

from tests.guards.find_unannotated_runtimes import find_unannotated_runtimes

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class RuntimeAnnotationsOfThePackageTest(unittest.TestCase):
    def test_should_find_every_runtime_parameter_annotated_as_a_runtime(self):
        # Act
        violations = find_unannotated_runtimes(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class RuntimeAnnotationsGuardTest(unittest.TestCase):
    def test_should_flag_a_runtime_parameter_without_its_annotation(self):
        rows = [
            (
                "a public function",
                "def run_segment(plan, number: int, runtime) -> None:\n    pass\n",
                "brigade/module.py:1 run_segment takes runtime without runtime: Runtime",
            ),
            (
                "a private function",
                "import os\n\n\ndef _tick(runtime) -> None:\n    pass\n",
                "brigade/module.py:4 _tick takes runtime without runtime: Runtime",
            ),
            (
                "a method",
                "class Caller:\n    def answer(self, runtime) -> None:\n        pass\n",
                "brigade/module.py:2 answer takes runtime without runtime: Runtime",
            ),
            (
                "a keyword-only parameter",
                "def install(request: dict, *, runtime) -> None:\n    pass\n",
                "brigade/module.py:1 install takes runtime without runtime: Runtime",
            ),
            (
                "another annotation",
                "def read_projects(runtime: object) -> None:\n    pass\n",
                "brigade/module.py:1 read_projects takes runtime without runtime: Runtime",
            ),
        ]
        for case, source, expected_violation in rows:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / "brigade" / "module.py"
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_unannotated_runtimes(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_let_a_runtime_annotated_as_a_runtime_and_a_function_taking_none_pass(self):
        rows = [
            ("an annotated runtime", "def read_projects(runtime: Runtime) -> None:\n    pass\n"),
            ("no runtime", "def plan(snapshot) -> None:\n    pass\n"),
        ]
        for case, source in rows:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / "brigade" / "module.py"
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_unannotated_runtimes(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [])
