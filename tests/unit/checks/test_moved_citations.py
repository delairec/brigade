import unittest

from brigade.checks.moved_citations import check
from tests.unit.create_test_runtime import create_test_runtime


def create_subject(citations: list) -> dict:
    return {
        "schema_version": 1,
        "project": "/srv/shop",
        "parameters": {"task": "B9"},
        "collected": {
            "draft": {
                "summary": {
                    "task": "B9",
                    "after": [],
                    "source_commit": "2222222222222222222222222222222222222222",
                    "files": [],
                    "entities": [],
                    "citations": citations,
                },
                "items": [],
            }
        },
    }


class MovedCitationsCheckTest(unittest.TestCase):
    def test_should_report_a_citation_whose_lines_moved_with_where_they_stand(self):
        # Arrange
        subject = create_subject(
            [
                {
                    "citation": "brigade/cart.py:3-4",
                    "path": "brigade/cart.py",
                    "start": 3,
                    "end": 4,
                    "now": {"start": 5, "end": 6},
                },
                {
                    "citation": "brigade/till.py:7",
                    "path": "brigade/till.py",
                    "start": 7,
                    "end": 7,
                    "now": {"start": 7, "end": 7},
                },
            ]
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "name": "moved_citations",
                "verdict": "fail",
                "findings": ["brigade/cart.py:3-4 moved since 22222222 to brigade/cart.py:5-6"],
            },
        )

    def test_should_report_a_citation_whose_lines_changed(self):
        # Arrange
        subject = create_subject(
            [{"citation": "brigade/shelf.py:9", "path": "brigade/shelf.py", "start": 9, "end": 9, "now": None}]
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(document["findings"], ["brigade/shelf.py:9 changed since 22222222"])

    def test_should_name_a_single_line_where_it_now_stands(self):
        # Arrange
        subject = create_subject(
            [
                {
                    "citation": "brigade/till.py:7",
                    "path": "brigade/till.py",
                    "start": 7,
                    "end": 7,
                    "now": {"start": 8, "end": 8},
                }
            ]
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(document["findings"], ["brigade/till.py:7 moved since 22222222 to brigade/till.py:8"])

    def test_should_pass_a_draft_none_of_whose_citations_moved(self):
        # Arrange
        subject = create_subject(
            [
                {
                    "citation": "brigade/till.py:7",
                    "path": "brigade/till.py",
                    "start": 7,
                    "end": 7,
                    "now": {"start": 7, "end": 7},
                }
            ]
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(document, {"schema_version": 1, "name": "moved_citations", "verdict": "pass", "findings": []})
