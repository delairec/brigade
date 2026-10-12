import tempfile
import unittest
from pathlib import Path

from tests.guards.find_preparations_before_delimiters import find_preparations_before_delimiters

TESTS_ROOT = Path(__file__).resolve().parents[1]


class PreparationsBeforeDelimitersOfTheTestsTest(unittest.TestCase):
    def test_should_find_no_test_preparing_something_before_its_first_delimiter(self):
        # Act
        violations = find_preparations_before_delimiters(TESTS_ROOT)

        # Assert
        self.assertEqual(violations, [])


class PreparationsBeforeDelimitersGuardTest(unittest.TestCase):
    def test_should_let_a_test_opening_on_its_first_delimiter_pass(self):
        for case, source in [
            (
                "a body opening on # Arrange",
                (
                    "class SampleTest(unittest.TestCase):\n"
                    "    def test_should_greet(self):\n"
                    "        # Arrange\n"
                    "        name = 'Ada'\n"
                    "\n"
                    "        # Act\n"
                    "        greeting = greet(name)\n"
                ),
            ),
            (
                "a body opening on # Act",
                (
                    "class SampleTest(unittest.TestCase):\n"
                    "    def test_should_greet(self):\n"
                    "        # Act\n"
                    "        greeting = greet()\n"
                ),
            ),
            (
                "a helper of the test class",
                (
                    "class SampleTest(unittest.TestCase):\n"
                    "    def greet_everyone(self):\n"
                    "        names = ['Ada', 'Max']\n"
                    "        return greet(names)\n"
                ),
            ),
            (
                "a for over subTest opening on # Act",
                (
                    "class SampleTest(unittest.TestCase):\n"
                    "    def test_should_greet(self):\n"
                    "        for name in ['Ada', 'Max']:\n"
                    "            with self.subTest(name=name):\n"
                    "                # Act\n"
                    "                greeting = greet(name)\n"
                ),
            ),
        ]:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / "tests" / "test_sample.py"
                module.parent.mkdir()
                module.write_text(source)

                # Act
                violations = find_preparations_before_delimiters(Path(root) / "tests")

                # Assert
                self.assertEqual(violations, [])

    def test_should_flag_a_test_preparing_something_before_its_first_delimiter(self):
        for case, source, violation in [
            (
                "rows above # Arrange",
                (
                    "class SampleTest(unittest.TestCase):\n"
                    "    def test_should_greet(self):\n"
                    "        rows = ['Ada', 'Max']\n"
                    "        # Arrange\n"
                    "        names = rows\n"
                    "\n"
                    "        # Act\n"
                    "        greetings = greet(names)\n"
                ),
                "tests/test_sample.py:2 test_should_greet prepares something before its first delimiter",
            ),
            (
                "a for over subTest under rows bound above it",
                (
                    "class SampleTest(unittest.TestCase):\n"
                    "    def test_should_greet(self):\n"
                    "        rows = ['Ada', 'Max']\n"
                    "        for name in rows:\n"
                    "            with self.subTest(name=name):\n"
                    "                # Act\n"
                    "                greeting = greet(name)\n"
                ),
                "tests/test_sample.py:2 test_should_greet prepares something before its first delimiter",
            ),
            (
                "rows above # Arrange in a test below one opening on # Arrange",
                (
                    "class SampleTest(unittest.TestCase):\n"
                    "    def test_should_greet(self):\n"
                    "        # Arrange\n"
                    "        name = 'Ada'\n"
                    "\n"
                    "        # Act\n"
                    "        greeting = greet(name)\n"
                    "\n"
                    "    def test_should_greet_everyone(self):\n"
                    "        rows = ['Ada', 'Max']\n"
                    "        # Arrange\n"
                    "        names = rows\n"
                    "\n"
                    "        # Act\n"
                    "        greetings = greet(names)\n"
                ),
                "tests/test_sample.py:9 test_should_greet_everyone prepares something before its first delimiter",
            ),
        ]:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / "tests" / "test_sample.py"
                module.parent.mkdir()
                module.write_text(source)

                # Act
                violations = find_preparations_before_delimiters(Path(root) / "tests")

                # Assert
                self.assertEqual(violations, [violation])
