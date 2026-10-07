import contextlib
import io
import unittest

from brigade.cli import _describe_version, main


class DescribeVersionTest(unittest.TestCase):
    def test_should_describe_the_version_as_text(self):
        # Act
        text = _describe_version(False)

        # Assert
        self.assertEqual(text, "brigade 0.1.0")

    def test_should_describe_the_version_as_a_json_document(self):
        # Act
        text = _describe_version(True)

        # Assert
        self.assertEqual(text, '{"schema_version": 1, "version": "0.1.0"}')


class MainWhenOnlyTheVersionIsAskedTest(unittest.TestCase):
    def test_should_print_the_version_and_return_zero(self):
        # Arrange
        stdout = io.StringIO()

        # Act
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--version"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "brigade 0.1.0\n")

    def test_should_print_the_version_as_a_json_document(self):
        # Arrange
        stdout = io.StringIO()

        # Act
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--version", "--json"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), '{"schema_version": 1, "version": "0.1.0"}\n')


class MainWhenNoOptionIsGivenTest(unittest.TestCase):
    def test_should_refuse_with_the_usage(self):
        # Arrange
        stderr = io.StringIO()

        # Act
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            main([])

        # Assert
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("no option given", stderr.getvalue())


class MainWhenAnUnrecognizedArgumentIsGivenTest(unittest.TestCase):
    def test_should_refuse_naming_the_argument(self):
        # Arrange
        stderr = io.StringIO()

        # Act
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            main(["--frobnicate"])

        # Assert
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("unrecognized arguments: --frobnicate", stderr.getvalue())
