import unittest

from brigade.errors import BrigadeError
from brigade.system.actions_request import ActionsRequest
from brigade.system.read_client_request import read_client_request


class ReadClientRequestTest(unittest.TestCase):
    def test_should_read_the_request_of_the_operation(self):
        # Act
        request = read_client_request("actions", '{"schema_version": 1, "output": "Reading the task"}')

        # Assert
        self.assertEqual(request, ActionsRequest(output="Reading the task"))

    def test_should_refuse_a_request_that_is_not_json(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_client_request("actions", "Reading the task")

        # Assert
        self.assertEqual(
            str(refusal.exception), "the request on stdin is not JSON: Expecting value: line 1 column 1 (char 0)"
        )

    def test_should_refuse_a_request_off_the_shape_of_the_operation(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_client_request("actions", '{"schema_version": 1}')

        # Assert
        self.assertEqual(str(refusal.exception), "the request on stdin: lacks the key output")
