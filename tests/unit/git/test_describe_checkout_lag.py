import tempfile
import unittest
from pathlib import Path

from brigade.errors import ToolFailure
from brigade.git.describe_checkout_lag import describe_checkout_lag
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner


class DescribeCheckoutLagTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.checkout = self.root / "checkout"
        (self.checkout / "brigade").mkdir(parents=True)
        self.package_file = self.checkout / "brigade" / "__init__.py"

    def test_should_describe_a_checkout_behind_its_upstream(self):
        # Arrange
        git = ScriptedProcessRunner(
            {
                ("git", "for-each-ref"): ProcessAnswer(stdout="*\tde446f3\torigin/main\n"),
                ("git", "rev-parse"): ProcessAnswer(stdout="8885daa\n"),
                ("git", "rev-list"): ProcessAnswer(stdout="1\t0\n"),
            }
        )

        # Act
        lag = describe_checkout_lag(git.run, self.package_file)

        # Assert
        self.assertEqual(lag, f"{self.checkout} at de446f3, 1 behind origin/main at 8885daa")

    def test_should_describe_the_failure_of_git_on_the_checkout(self):
        # Arrange
        git = ScriptedProcessRunner({("git", "for-each-ref"): ToolFailure("git for-each-ref timed out after 10 s")})

        # Act
        lag = describe_checkout_lag(git.run, self.package_file)

        # Assert
        self.assertEqual(lag, f"{self.checkout}: git for-each-ref timed out after 10 s")

    def test_should_describe_no_lag_for_a_checkout_up_to_date(self):
        # Arrange
        git = ScriptedProcessRunner(
            {
                ("git", "for-each-ref"): ProcessAnswer(stdout="*\tde446f3\torigin/main\n"),
                ("git", "rev-parse"): ProcessAnswer(stdout="de446f3\n"),
                ("git", "rev-list"): ProcessAnswer(stdout="0\t0\n"),
            }
        )

        # Act
        lag = describe_checkout_lag(git.run, self.package_file)

        # Assert
        self.assertIsNone(lag)

    def test_should_describe_no_lag_when_brigade_runs_from_an_archive(self):
        # Arrange
        archive = self.root / "dist" / "brigade.pyz"
        archive.parent.mkdir()
        archive.write_text("")
        git_never_asked = ScriptedProcessRunner({})

        # Act
        lag = describe_checkout_lag(git_never_asked.run, archive / "brigade" / "__init__.py")

        # Assert
        self.assertIsNone(lag)
