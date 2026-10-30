import unittest

from brigade.system.pull_request_facts import PullRequestFacts


class PullRequestFactsTest(unittest.TestCase):
    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {
            "number": 160,
            "state": "open",
            "checks": [{"name": "unit", "verdict": "success"}],
            "review": None,
            "behind": False,
            "head": "4f2a9c1",
            "base": "integration/M1",
            "updated_at": "2026-10-30T14:04:22Z",
        }

        # Act
        written = PullRequestFacts.from_document(document).to_document()

        # Assert
        self.assertEqual(
            written,
            {
                "number": 160,
                "state": "open",
                "checks": [{"name": "unit", "verdict": "success"}],
                "review": None,
                "behind": False,
                "head": "4f2a9c1",
                "base": "integration/M1",
                "updated_at": "2026-10-30T14:04:22Z",
            },
        )
