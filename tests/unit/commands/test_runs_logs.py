import argparse
import contextlib
import io
import unittest

from brigade.add_command_parsers import add_command_parsers
from brigade.commands.runs_logs import COMMAND


class RunsLogsWithATailOfNoLineTest(unittest.TestCase):
    def test_should_refuse_the_count(self):
        # Arrange
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (COMMAND,), argparse.ArgumentParser(add_help=False))
        errors = io.StringIO()

        # Act
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(errors):
            parser.parse_args(["runs", "logs", "20261007T142949Z-327ab0", "--tail", "0"])

        # Assert
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("'0' is not a count of 1 or more", errors.getvalue())
