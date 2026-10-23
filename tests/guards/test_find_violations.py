import tempfile
import unittest
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations


def _find_assignments(module: GuardedModule) -> list[Finding]:
    return [(node.lineno, node.col_offset, f"assigns in {module.relative_path.name}") for node in module.tree.body]


def _find_names_in_reverse(module: GuardedModule) -> list[Finding]:
    return [(1, 4, "reads second"), (2, 0, "reads third"), (1, 0, "reads first")]


def _inspect_outside_vendor(relative_path: Path) -> bool:
    return relative_path.parts[0] != "vendor"


class FindViolationsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name) / "brigade"

    def tearDown(self):
        self.directory.cleanup()

    def write_module(self, module_path: str, source: str) -> None:
        module = self.root / module_path
        module.parent.mkdir(parents=True, exist_ok=True)
        module.write_text(source)

    def test_should_locate_each_finding_by_the_root_name_the_module_path_and_its_line(self):
        # Arrange
        self.write_module("runs/read_run.py", "import json\nrun = 1\n")

        # Act
        violations = find_violations(self.root, _find_assignments)

        # Assert
        self.assertEqual(
            violations,
            ["brigade/runs/read_run.py:1 assigns in read_run.py", "brigade/runs/read_run.py:2 assigns in read_run.py"],
        )

    def test_should_order_the_findings_of_a_module_by_line_then_column(self):
        # Arrange
        self.write_module("read_run.py", "run = 1\n")

        # Act
        violations = find_violations(self.root, _find_names_in_reverse)

        # Assert
        self.assertEqual(
            violations,
            [
                "brigade/read_run.py:1 reads first",
                "brigade/read_run.py:1 reads second",
                "brigade/read_run.py:2 reads third",
            ],
        )

    def test_should_walk_the_modules_in_path_order(self):
        # Arrange
        self.write_module("tick/run_tick.py", "tick = 1\n")
        self.write_module("runs/read_run.py", "run = 1\n")

        # Act
        violations = find_violations(self.root, _find_assignments)

        # Assert
        self.assertEqual(
            violations,
            ["brigade/runs/read_run.py:1 assigns in read_run.py", "brigade/tick/run_tick.py:1 assigns in run_tick.py"],
        )

    def test_should_leave_a_module_the_filter_excludes(self):
        # Arrange
        self.write_module("vendor/read_toml.py", "toml = 1\n")

        # Act
        violations = find_violations(self.root, _find_assignments, is_inspected=_inspect_outside_vendor)

        # Assert
        self.assertEqual(violations, [])

    def test_should_inspect_only_the_modules_the_pattern_matches(self):
        # Arrange
        self.write_module("helpers.py", "helper = 1\n")
        self.write_module("test_run.py", "test = 1\n")

        # Act
        violations = find_violations(self.root, _find_assignments, pattern="test_*.py")

        # Assert
        self.assertEqual(violations, ["brigade/test_run.py:1 assigns in test_run.py"])
