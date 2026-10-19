import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.waves.describe_request import describe_request


class DescribeRequestTest(unittest.TestCase):
    def test_should_describe_a_planned_request_by_its_project_milestone_and_branch(self):
        # Arrange
        request = Entity(
            name="oak_1",
            fields=(
                EntityField(name="PROJECT", value="@PROJECT.oak"),
                EntityField(name="STATUS", value="planned"),
                EntityField(name="MILESTONE", value="F0"),
                EntityField(name="BRANCH", value="integration/F0-parser"),
                EntityField(name="CREATED_AT", value="2026-10-19T09:00:00Z"),
            ),
        )

        # Act
        described = describe_request(request)

        # Assert
        self.assertEqual(
            described,
            {
                "name": "oak_1",
                "project": "oak",
                "status": "planned",
                "milestone": "F0",
                "branch": "integration/F0-parser",
                "created_at": "2026-10-19T09:00:00Z",
            },
        )
