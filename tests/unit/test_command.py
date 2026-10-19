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
            read_request=vars,
            render_text=str,
            decide_exit_code=len,
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
