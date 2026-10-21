import tempfile
import unittest
from pathlib import Path

from tests.guards.find_tool_argvs import find_tool_argvs

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class ToolArgvsOfTheBrigadePackageTest(unittest.TestCase):
    def test_should_find_no_argv_opening_on_awawa_or_git_outside_their_gateways(self):
        # Act
        violations = find_tool_argvs(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class ToolArgvsGuardTest(unittest.TestCase):
    def inspect(self, module_path: str, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / module_path
            module.parent.mkdir(parents=True)
            module.write_text(source)
            return find_tool_argvs(Path(root) / "brigade")

    def test_should_flag_a_tuple_or_a_list_opening_on_awawa_or_git(self):
        # Arrange
        rows = [
            (
                "brigade/planning/read_plan.py",
                'argv = ("awawa", "show", target)\n',
                "brigade/planning/read_plan.py:1 builds an argv opening on awawa",
            ),
            (
                "brigade/planning/read_plan.py",
                'import json\nrun(["awawa", *arguments])\n',
                "brigade/planning/read_plan.py:2 builds an argv opening on awawa",
            ),
            (
                "brigade/tasks/promote_task.py",
                'argv = ("git", "status")\n',
                "brigade/tasks/promote_task.py:1 builds an argv opening on git",
            ),
            (
                "brigade/tasks/promote_task.py",
                'run(["git", "log", "-1"])\n',
                "brigade/tasks/promote_task.py:1 builds an argv opening on git",
            ),
        ]
        for module_path, source, expected_violation in rows:
            with self.subTest(source=source):
                # Act
                violations = self.inspect(module_path, source)

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_leave_a_call_taking_awawa_or_git_as_a_label(self):
        # Arrange
        source = '_create_prerequisite("awawa", "ok", version)\n_create_prerequisite("git", "finding", "not on PATH")\n'

        # Act
        violations = self.inspect("brigade/commands/doctor.py", source)

        # Assert
        self.assertEqual(violations, [])

    def test_should_leave_the_argvs_of_the_awawa_and_git_gateways(self):
        # Arrange
        rows = [
            ("brigade/corpus/read_schema.py", 'argv = ("awawa", "show", entity_type)\n'),
            ("brigade/git/commit_files.py", 'argv = ["git", "commit"]\n'),
        ]
        for module_path, source in rows:
            with self.subTest(module=module_path):
                # Act
                violations = self.inspect(module_path, source)

                # Assert
                self.assertEqual(violations, [])
