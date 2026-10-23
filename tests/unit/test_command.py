import argparse
import unittest

from brigade.command import Command


def run_nothing(request, runtime):
    return {"runs": []}


class CommandByDefaultTest(unittest.TestCase):
    def setUp(self):
        self.command = Command(
            path=("runs", "list"),
            help="list the runs",
            run=run_nothing,
            render_text=str,
        )

    def test_should_describe_no_diagnostic(self):
        # Act
        diagnostics = self.command.describe_diagnostics({"runs": []})

        # Assert
        self.assertEqual(diagnostics, [])

    def test_should_select_the_whole_result_as_its_document(self):
        # Arrange
        result = {"runs": []}

        # Act
        document = self.command.select_document(result)

        # Assert
        self.assertIs(document, result)

    def test_should_read_the_options_themselves_as_its_request(self):
        # Arrange
        options = argparse.Namespace(project="brigade")

        # Act
        request = self.command.read_request(options)

        # Assert
        self.assertIs(request, options)

    def test_should_exit_0_whatever_its_document(self):
        # Arrange
        document_with_runs = {"runs": [{"id": "20261023T002843Z-6c3f7e"}]}

        # Act
        exit_code = self.command.decide_exit_code(document_with_runs)

        # Assert
        self.assertEqual(exit_code, 0)
