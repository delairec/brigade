import unittest

from brigade.checks.reviewed import check
from tests.unit.create_test_runtime import create_test_runtime


def create_subject(pull_requests: list) -> dict:
    return {
        "schema_version": 1,
        "project": "/srv/shop",
        "parameters": {"pr": "12"},
        "collected": {"pr-list": {"summary": {"open": len(pull_requests)}, "items": pull_requests}},
    }


class ReviewedCheckTest(unittest.TestCase):
    def test_should_fail_on_a_pull_request_no_review_was_submitted_on(self):
        # Arrange
        subject = create_subject([{"number": 12, "reviews": 0}])

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "name": "reviewed",
                "verdict": "fail",
                "findings": ["no review was submitted on the pull request 12"],
            },
        )

    def test_should_pass_on_a_pull_request_a_review_was_submitted_on(self):
        # Arrange
        subject = create_subject([{"number": 11, "reviews": 0}, {"number": 12, "reviews": 1}])

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(document, {"schema_version": 1, "name": "reviewed", "verdict": "pass", "findings": []})

    def test_should_fail_on_a_pull_request_the_forge_does_not_list(self):
        # Arrange
        subject = create_subject([{"number": 11, "reviews": 2}])

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "name": "reviewed",
                "verdict": "fail",
                "findings": ["the forge lists no pull request 12"],
            },
        )
