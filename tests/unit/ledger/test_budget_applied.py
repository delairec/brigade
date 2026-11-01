import unittest

from brigade.ledger.budget_applied import BudgetApplied


class BudgetAppliedTest(unittest.TestCase):
    def test_should_read_the_change_of_the_cap_of_a_role_with_the_measures_it_was_computed_from(self):
        # Act
        event = BudgetApplied.from_document(
            {
                "event": "budget.applied",
                "role": "ada",
                "before": 75,
                "after": 63,
                "segments": 6,
                "restarts": 3,
                "growth": 100.0,
                "restart_tokens": 200000.0,
            }
        )

        # Assert
        self.assertEqual(
            event,
            BudgetApplied(
                role="ada", before=75, after=63, segments=6, restarts=3, growth=100.0, restart_tokens=200000.0
            ),
        )
