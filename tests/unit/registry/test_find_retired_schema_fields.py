import unittest

from brigade.corpus.shipped_data import SHIPPED_SCHEMA
from brigade.registry.find_retired_schema_fields import RetiredName, find_retired_schema_fields

POLICY_WITH_VERIFY_ROUNDS = """SCHEMA POLICY
\tDESC "how far a project's waves run on their own"
\tFIELD PROJECT @PROJECT
\t\tREQUIRED
\tFIELD VERIFY_ROUNDS uint
\t\tDEFAULT 2
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
