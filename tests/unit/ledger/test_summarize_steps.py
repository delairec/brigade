import unittest

from brigade.ledger.summarize_steps import summarize_steps


class SummarizeSteps(unittest.TestCase):
    def test_should_give_the_p50_and_p90_by_nearest_rank_and_count_the_runs_without_steps(self):
        rows = [
            ([], {"measured": 0, "unmeasured": 0, "p50": None, "p90": None}),
            ([None, None], {"measured": 0, "unmeasured": 2, "p50": None, "p90": None}),
            ([31], {"measured": 1, "unmeasured": 0, "p50": 31, "p90": 31}),
            ([50, 30], {"measured": 2, "unmeasured": 0, "p50": 30, "p90": 50}),
            ([90, 80, None, 10, 20, 30], {"measured": 5, "unmeasured": 1, "p50": 30, "p90": 90}),
            ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], {"measured": 10, "unmeasured": 0, "p50": 5, "p90": 9}),
            ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], {"measured": 11, "unmeasured": 0, "p50": 6, "p90": 10}),
        ]
        for steps, expected_summary in rows:
            with self.subTest(steps=steps):
                # Act
                summary = summarize_steps(steps)

                # Assert
                self.assertEqual(summary, expected_summary)
