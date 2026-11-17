import unittest

from brigade.corpus.shipped_data import SHIPPED_SCHEMA
from brigade.registry.find_retired_schema_fields import find_retired_schema_fields
from brigade.system.retired_name import RetiredName

POLICY_WITH_VERIFY_ROUNDS = """SCHEMA POLICY
\tDESC "how far a project's waves run on their own"
\tFIELD PROJECT @PROJECT
\t\tREQUIRED
\tFIELD VERIFY_ROUNDS uint
\t\tDEFAULT 2
"""

ANSWER_WITH_COLLECTED_DOCUMENT = """SCHEMA ANSWER
\tFIELD COLLECTED string
\t\tREPEATABLE
\t\tFIELD SUMMARY string
\t\t\tREQUIRED
\t\tFIELD DOCUMENT string
\t\t\tREQUIRED
"""

PROJECT_WITH_VERIFY_ROUNDS = """SCHEMA PROJECT
\tFIELD VERIFY_ROUNDS uint
"""


class FindRetiredSchemaFieldsTest(unittest.TestCase):
    def test_should_name_a_retired_field_of_the_policy_with_its_new_name(self):
        # Act
        retired = find_retired_schema_fields(POLICY_WITH_VERIFY_ROUNDS)

        # Assert
        self.assertEqual(retired, [RetiredName(old="POLICY.VERIFY_ROUNDS", new="POLICY.REPAIR_ROUNDS")])

    def test_should_name_a_retired_field_nested_under_another_with_its_new_name(self):
        # Act
        retired = find_retired_schema_fields(ANSWER_WITH_COLLECTED_DOCUMENT)

        # Assert
        self.assertEqual(retired, [RetiredName(old="ANSWER.DOCUMENT", new="ANSWER.COLLECTION")])

    def test_should_find_no_retired_field_in_the_shipped_schema(self):
        # Act
        retired = find_retired_schema_fields(SHIPPED_SCHEMA.read_text())

        # Assert
        self.assertEqual(retired, [])

    def test_should_leave_a_field_of_a_retired_name_declared_by_another_type(self):
        # Act
        retired = find_retired_schema_fields(PROJECT_WITH_VERIFY_ROUNDS)

        # Assert
        self.assertEqual(retired, [])
