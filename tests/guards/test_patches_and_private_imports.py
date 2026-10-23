import tempfile
import unittest
from pathlib import Path

from tests.guards.find_patches_and_private_imports import find_patches_and_private_imports

TESTS_ROOT = Path(__file__).resolve().parents[1]


class PatchesAndPrivateImportsOfTheTestsTest(unittest.TestCase):
    def test_should_find_no_patch_and_no_private_import_in_the_tests(self):
        # Act
        violations = find_patches_and_private_imports(TESTS_ROOT)

        # Assert
        self.assertEqual(violations, [])


class PatchesAndPrivateImportsGuardTest(unittest.TestCase):
    def inspect(self, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "tests" / "unit" / "test_greeter.py"
            module.parent.mkdir(parents=True)
            module.write_text(source)
            return find_patches_and_private_imports(Path(root) / "tests")

    def test_should_flag_every_form_of_a_patch(self):
        # Arrange
        rows = [
            ("a patch", "from unittest import mock\n\nwith mock.patch('os.kill'):\n    pass\n", 3),
            ("a patch of a mapping", "from unittest import mock\n\nmock.patch.dict(os.environ, {}).start()\n", 3),
            ("a patch of an attribute", "import unittest.mock\n\nunittest.mock.patch.object(sys, 'argv').start()\n", 3),
            ("the patch imported", "from unittest.mock import patch\n", 1),
        ]
        for case, source, line in rows:
            with self.subTest(case=case):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, [f"tests/unit/test_greeter.py:{line} patches a name through unittest.mock"])

    def test_should_flag_the_import_of_an_underscored_name(self):
        # Arrange
        source = "from brigade.commands.doctor import _check_checkout, describe_doctor\n"

        # Act
        violations = self.inspect(source)

        # Assert
        self.assertEqual(violations, ["tests/unit/test_greeter.py:1 imports the private name _check_checkout"])

    def test_should_let_a_double_and_a_public_import_pass(self):
        # Arrange
        rows = [
            ("a double of the mock module", "from unittest import mock\n\nreader = mock.Mock(return_value='')\n"),
            ("a public name", "from brigade.commands.doctor import describe_doctor\n"),
            ("a public name of a module whose name opens on an underscore", "from brigade._launch import launch\n"),
        ]
        for case, source in rows:
            with self.subTest(case=case):
                # Act
                violations = self.inspect(source)

                # Assert
                self.assertEqual(violations, [])
