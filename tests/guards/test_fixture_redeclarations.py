import tempfile
import unittest
from pathlib import Path

from tests.guards.find_fixture_redeclarations import find_fixture_redeclarations

TESTS_ROOT = Path(__file__).resolve().parents[1]


class FixtureRedeclarationsOfTheTestsTest(unittest.TestCase):
    def test_should_find_no_stand_in_namespace_and_no_second_declaration_of_a_shared_fixture(self):
        # Act
        violations = find_fixture_redeclarations(TESTS_ROOT)

        # Assert
        self.assertEqual(violations, [])


class FixtureRedeclarationsGuardTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.tests_root = Path(self.directory.name) / "tests"

    def tearDown(self):
        self.directory.cleanup()

    def inspect(self, module_path: str, source: str) -> list[str]:
        module = self.tests_root / module_path
        module.parent.mkdir(parents=True, exist_ok=True)
        module.write_text(source)
        return find_fixture_redeclarations(self.tests_root)

    def test_should_flag_every_reference_to_a_simple_namespace(self):
        # Arrange
        source = (
            "import types\nfrom types import SimpleNamespace\n\n"
            "runner = types.SimpleNamespace(run=None)\nclock = SimpleNamespace(now=None)\n"
        )

        # Act
        violations = self.inspect("unit/test_greeter.py", source)

        # Assert
        self.assertEqual(
            violations,
            [
                "tests/unit/test_greeter.py:2 SimpleNamespace stands in for the record or the double it imitates",
                "tests/unit/test_greeter.py:4 SimpleNamespace stands in for the record or the double it imitates",
                "tests/unit/test_greeter.py:5 SimpleNamespace stands in for the record or the double it imitates",
            ],
        )

    def test_should_flag_a_shared_fixture_declared_outside_its_module(self):
        for case, source, expected_violation in [
            (
                "a class",
                "class ForgeDouble:\n    pass\n",
                (
                    "tests/unit/test_greeter.py:1 ForgeDouble is declared again, its declaration being"
                    " tests/unit/forge_double.py"
                ),
            ),
            (
                "a function",
                "def try_lock(path):\n    return True\n",
                (
                    "tests/unit/test_greeter.py:1 try_lock is declared again, its declaration being"
                    " tests/unit/system/try_lock.py"
                ),
            ),
            (
                "a module constant",
                "IDENTITY = ()\n",
                (
                    "tests/unit/test_greeter.py:1 IDENTITY is declared again, its declaration being"
                    " tests/integration/repository_test_case.py"
                ),
            ),
        ]:
            with self.subTest(case=case):
                # Act
                violations = self.inspect("unit/test_greeter.py", source)

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_leave_a_shared_fixture_declared_in_its_module(self):
        # Arrange
        source = "class ForgeDouble:\n    pass\n"

        # Act
        violations = self.inspect("unit/forge_double.py", source)

        # Assert
        self.assertEqual(violations, [])
