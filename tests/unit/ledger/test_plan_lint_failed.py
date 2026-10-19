import unittest

from brigade.ledger.plan_lint_failed import PlanLintFailed


class PlanLintFailedTest(unittest.TestCase):
    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"request": "req-1", "run": None}

        # Act
        written = PlanLintFailed.from_document(document).to_document()

        # Assert
        self.assertEqual(written, {"request": "req-1", "run": None})
