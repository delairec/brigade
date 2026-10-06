import unittest

from brigade.system.validate_document import DocumentInvalid, Field, validate_document

SHAPE = {
    "schema_version": Field(kinds=(int,), values=(1,)),
    "outcome": Field(kinds=(str,), values=("done", "failed")),
    "steps": Field(kinds=(int,), nullable=True),
    "argv": Field(kinds=(list,), items=Field(kinds=(str,)), non_empty=True),
    "usage": Field(kinds=(dict,), nullable=True, fields={"input_tokens": Field(kinds=(int,))}),
    "content": Field(kinds=(str, list)),
}


class ValidateDocumentWhenTheDocumentFitsItsShape(unittest.TestCase):
    def test_should_accept_it(self):
        # Arrange
        document = {
            "schema_version": 1,
            "outcome": "done",
            "steps": None,
            "argv": ["claude", "--print"],
            "usage": {"input_tokens": 9, "service_tier": "standard"},
            "content": [],
            "comment": "a key the shape does not declare",
        }

        # Act
        verdict = validate_document(document, SHAPE)

        # Assert
        self.assertIsNone(verdict)


class ValidateDocumentWhenTheDocumentDepartsFromItsShape(unittest.TestCase):
    def test_should_name_the_key_and_what_is_wrong_with_it(self):
        rows = [
            (
                "a missing key",
                {"schema_version": 1, "steps": 1, "argv": ["claude"], "usage": None, "content": ""},
                "lacks the key outcome",
            ),
            (
                "a missing nested key",
                {"schema_version": 1, "outcome": "done", "steps": 1, "argv": ["claude"], "usage": {}, "content": ""},
                "lacks the key usage.input_tokens",
            ),
            (
                "a wrong type",
                {
                    "schema_version": 1,
                    "outcome": "done",
                    "steps": "3",
                    "argv": ["claude"],
                    "usage": None,
                    "content": "",
                },
                "steps is a string, not an integer",
            ),
            (
                "a boolean for an integer",
                {
                    "schema_version": 1,
                    "outcome": "done",
                    "steps": True,
                    "argv": ["claude"],
                    "usage": None,
                    "content": "",
                },
                "steps is a boolean, not an integer",
            ),
            (
                "a null where none is allowed",
                {"schema_version": 1, "outcome": None, "steps": 1, "argv": ["claude"], "usage": None, "content": ""},
                "outcome is null, not a string",
            ),
            (
                "a value outside its enumeration",
                {"schema_version": 1, "outcome": "maybe", "steps": 1, "argv": ["claude"], "usage": None, "content": ""},
                "outcome is 'maybe', not one of done, failed",
            ),
            (
                "an unknown schema version",
                {"schema_version": 2, "outcome": "done", "steps": 1, "argv": ["claude"], "usage": None, "content": ""},
                "schema_version is 2, not one of 1",
            ),
            (
                "a wrong list item",
                {
                    "schema_version": 1,
                    "outcome": "done",
                    "steps": 1,
                    "argv": ["claude", 3],
                    "usage": None,
                    "content": "",
                },
                "argv[1] is an integer, not a string",
            ),
            (
                "an empty list where one item at least is required",
                {"schema_version": 1, "outcome": "done", "steps": 1, "argv": [], "usage": None, "content": ""},
                "argv is an empty list",
            ),
            (
                "a value of none of its kinds",
                {"schema_version": 1, "outcome": "done", "steps": 1, "argv": ["claude"], "usage": None, "content": 7},
                "content is an integer, not a string or a list",
            ),
        ]
        for case, document, expected_message in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(DocumentInvalid) as raised:
                    validate_document(document, SHAPE)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)

    def test_should_refuse_a_document_that_is_not_an_object(self):
        # Arrange
        a_list = ["schema_version", 1]

        # Act
        with self.assertRaises(DocumentInvalid) as raised:
            validate_document(a_list, SHAPE)

        # Assert
        self.assertEqual(str(raised.exception), "the document is a list, not an object")
