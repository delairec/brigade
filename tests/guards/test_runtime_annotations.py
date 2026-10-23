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
        # Arrange
        rows = [
            (
                "a public function",
                "def run_segment(plan: RunPlan, number: int, runtime) -> None:\n    pass\n",
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
            (
                "a variadic parameter",
                "def collect(*runtime) -> None:\n    pass\n",
                "brigade/module.py:1 collect takes runtime without runtime: Runtime",
            ),
            (
                "a keyword variadic parameter",
                "def collect(**runtime) -> None:\n    pass\n",
                "brigade/module.py:1 collect takes runtime without runtime: Runtime",
            ),
            (
                "a lambda",
                "handler = lambda runtime: None\n",
                "brigade/module.py:1 a lambda takes runtime without runtime: Runtime",
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
        # Arrange
        rows = [
            ("an annotated runtime", "def read_projects(runtime: Runtime) -> None:\n    pass\n"),
            ("no runtime", "def plan(snapshot: Snapshot) -> None:\n    pass\n"),
            ("an annotated variadic parameter", "def collect(*runtime: Runtime) -> None:\n    pass\n"),
            ("an annotated keyword variadic parameter", "def collect(**runtime: Runtime) -> None:\n    pass\n"),
            ("a lambda taking no runtime", "handler = lambda: None\n"),
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


class PublicSignatureAnnotationsGuardTest(unittest.TestCase):
    def test_should_flag_a_public_parameter_or_return_without_its_annotation(self):
        # Arrange
        rows = [
            (
                "a parameter",
                "def plan(snapshot) -> None:\n    pass\n",
                "brigade/module.py:1 plan leaves snapshot unannotated",
            ),
            (
                "a return",
                "def plan(snapshot: Snapshot):\n    pass\n",
                "brigade/module.py:1 plan leaves its return unannotated",
            ),
            (
                "a method parameter",
                "class Parser:\n    def error(self, message) -> NoReturn:\n        pass\n",
                "brigade/module.py:2 error leaves message unannotated",
            ),
            (
                "a keyword-only parameter",
                "def install(request: dict, *, force) -> None:\n    pass\n",
                "brigade/module.py:1 install leaves force unannotated",
            ),
            (
                "a variadic parameter",
                "def collect(*inputs) -> None:\n    pass\n",
                "brigade/module.py:1 collect leaves inputs unannotated",
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

    def test_should_let_a_private_function_and_the_receiver_of_a_method_pass(self):
        # Arrange
        rows = [
            ("a private function", "def _plan(snapshot):\n    pass\n"),
            ("an instance method", "class Parser:\n    def error(self, message: str) -> None:\n        pass\n"),
            ("a class method", "class Parser:\n    @classmethod\n    def build(cls) -> None:\n        pass\n"),
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
