import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.waves.describe_request import describe_request


class DescribeRequestTest(unittest.TestCase):
    def test_should_describe_a_planned_request_by_its_project_milestone_and_pull_request(self):
        # Arrange
        request = Entity(
            name="oak_r1",
            fields=(
                EntityField(name="PROJECT", value="@PROJECT.oak"),
                EntityField(name="STATUS", value="planned"),
                EntityField(name="MILESTONE", value="F0"),
                EntityField(name="PR", value="42"),
                EntityField(name="CREATED_AT", value="2026-10-19T09:00:00Z"),
            ),
        )

        # Act
        described = describe_request(request)

        # Assert
        self.assertEqual(
            described,
            {
                "name": "oak_r1",
                "project": "oak",
                "status": "planned",
                "milestone": "F0",
                "pr": 42,
                "created_at": "2026-10-19T09:00:00Z",
            },
        )

    def test_should_describe_a_request_still_planning_with_no_pull_request(self):
        # Arrange
        request = Entity(
            name="oak_r2",
            fields=(
                EntityField(name="PROJECT", value="@PROJECT.oak"),
                EntityField(name="STATUS", value="planning"),
                EntityField(name="CREATED_AT", value="2026-10-19T09:00:00Z"),
            ),
        )

        # Act
        described = describe_request(request)

        # Assert
        self.assertEqual(
            described,
            {
                "name": "oak_r2",
                "project": "oak",
                "status": "planning",
                "milestone": None,
                "pr": None,
                "created_at": "2026-10-19T09:00:00Z",
            },
        )
