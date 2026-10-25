import unittest

from brigade.studies.describe_triage import describe_triage
from tests.unit.studies.built_in_triage import BUILT_IN_TRIAGE


class DescribeTriageTest(unittest.TestCase):
    def test_should_describe_the_daily_triage_of_the_inbox_families_into_patterns(self):
        # Act
        study = describe_triage()

        # Assert
        self.assertEqual(study, BUILT_IN_TRIAGE)
