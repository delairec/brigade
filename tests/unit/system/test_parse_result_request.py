import unittest

from brigade.system.parse_result_request import ParseResultRequest

PARSE_RESULT_DOCUMENT = {"schema_version": 1, "exit_code": 0, "stdout": '{"result": "done"}', "stderr": ""}


class ParseResultRequestTest(unittest.TestCase):
    def test_should_write_back_the_document_it_read(self):
        # Act
        document = ParseResultRequest.from_document(PARSE_RESULT_DOCUMENT).to_document()

        # Assert
        self.assertEqual(document, {"schema_version": 1, "exit_code": 0, "stdout": '{"result": "done"}', "stderr": ""})
