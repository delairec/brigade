import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.require_answer_type import require_answer_type

CORPUS = Path("/srv/corpus")
DECLARED_TYPES = {(CORPUS, "FINDING")}


def check_type_declared(root: Path, entity_type: str) -> bool:
    return (root, entity_type) in DECLARED_TYPES


class RequireAnswerTypeTest(unittest.TestCase):
    def test_should_accept_a_type_the_schema_declares(self):
        # Act
        required = require_answer_type(check_type_declared, CORPUS, "FINDING")

        # Assert
        self.assertIsNone(required)

    def test_should_refuse_a_type_the_schema_does_not_declare(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            require_answer_type(check_type_declared, CORPUS, "VERDICT")

        # Assert
        self.assertEqual(str(refusal.exception), "the schema of the operational corpus declares no VERDICT")
