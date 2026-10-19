import unittest

from brigade.system.actions_request import ActionsRequest


class ActionsRequestTest(unittest.TestCase):
    def test_should_read_the_output_to_summarize(self):
        # Act
        request = ActionsRequest.from_document({"schema_version": 1, "output": "Reading the task\n"})

        # Assert
        self.assertEqual(request, ActionsRequest(output="Reading the task\n"))
