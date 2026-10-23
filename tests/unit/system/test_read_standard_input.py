import argparse
import io
import unittest

from brigade.system.read_standard_input import read_standard_input


class ReadStandardInputTest(unittest.TestCase):
    def test_should_read_the_whole_standard_input_the_command_line_was_given(self):
        # Arrange
        options = argparse.Namespace(standard_input=io.StringIO('{"schema_version": 1}\n'))

        # Act
        text = read_standard_input(options)

        # Assert
        self.assertEqual(text, '{"schema_version": 1}\n')
