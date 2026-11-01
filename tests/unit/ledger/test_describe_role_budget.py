import unittest

from brigade.ledger.describe_role_budget import CurrentDigests, RoleBudget, describe_role_budget
from brigade.ledger.run_finished import RunFinished
from brigade.system.token_usage import TokenUsage

ROLE_DIGEST = "3f1a"
OLDER_ROLE_DIGEST = "9c0d"
PROCEDURE_DIGEST = "7b2e"
SHIPPED_BUDGET = 75
LATEST_RECORDED = CurrentDigests(role=None, procedures={})
TURN_LIMIT = "turn_limit"
DONE = "done"
NOT_MEASURED = None


def _create_segment(run: str, segment: int, steps: int, tokens: int, outcome: str, **measures) -> RunFinished:
    return RunFinished(
        run=run,
        segment=segment,
        procedure="build-task",
        slot="build",
        role="ada",
        client="claude-code",
        project="brigade",
        session=None,
        main_steps=steps,
        total_steps=steps,
        duration_ms=1000,
        usage=TokenUsage(
            input_tokens=0, output_tokens=0, cache_creation_input_tokens=0, cache_read_input_tokens=tokens
        ),
        outcome=outcome,
        error_class=None,
        exit=0,
        wave=None,
        task=None,
        nulls={},
        tokens_to_first_edit=measures.get("tokens_to_first_edit"),
        role_digest=measures.get("role_digest", ROLE_DIGEST),
        procedure_digest=PROCEDURE_DIGEST,
    )


def _create_three_restarted_runs(restart_tokens: int) -> tuple[RunFinished, ...]:
    return (
        _create_segment("r1", 1, 10, 15000, TURN_LIMIT),
        _create_segment("r1", 2, 20, 40000, DONE, tokens_to_first_edit=restart_tokens),
        _create_segment("r2", 1, 30, 75000, TURN_LIMIT),
        _create_segment("r2", 2, 40, 120000, DONE, tokens_to_first_edit=restart_tokens),
        _create_segment("r3", 1, 50, 175000, TURN_LIMIT),
        _create_segment("r3", 2, 10, 15000, DONE, tokens_to_first_edit=restart_tokens),
    )


class DescribeRoleBudgetTest(unittest.TestCase):
    def test_should_apply_the_square_root_of_twice_the_restart_cost_over_the_growth(self):
        # Arrange
        segments = _create_three_restarted_runs(restart_tokens=200000)

        # Act
        budget = describe_role_budget(segments, SHIPPED_BUDGET, LATEST_RECORDED)

        # Assert
        self.assertEqual(
            budget,
            RoleBudget(
                shipped=75, computed=63, applied=63, segments=6, restarts=3, growth=100.0, restart_tokens=200000.0
            ),
        )

    def test_should_apply_a_computed_cap_within_half_and_double_the_shipped_budget(self):
        # Arrange
        rows = [("over double", 2000000, 200, 150), ("under half", 20000, 20, 38)]
        for case, restart_tokens, computed, applied in rows:
            with self.subTest(case=case):
                segments = _create_three_restarted_runs(restart_tokens)

                # Act
                budget = describe_role_budget(segments, SHIPPED_BUDGET, LATEST_RECORDED)

                # Assert
                self.assertEqual(budget.computed, computed)
                self.assertEqual(budget.applied, applied)

    def test_should_run_at_the_shipped_budget_below_five_segments_or_three_restarts(self):
        # Arrange
        rows = [
            (
                "four segments",
                (
                    _create_segment("r2", 1, 30, 75000, TURN_LIMIT),
                    _create_segment("r2", 2, 40, 120000, DONE, tokens_to_first_edit=200000),
                    _create_segment("r3", 1, 50, 175000, TURN_LIMIT),
                    _create_segment("r3", 2, 10, 15000, DONE, tokens_to_first_edit=200000),
                ),
            ),
            (
                "two restarts",
                (
                    _create_segment("r1", 1, 10, 15000, TURN_LIMIT),
                    _create_segment("r1", 2, 20, 40000, DONE, tokens_to_first_edit=200000),
                    _create_segment("r2", 1, 30, 75000, TURN_LIMIT),
                    _create_segment("r2", 2, 40, 120000, DONE, tokens_to_first_edit=200000),
                    _create_segment("r4", 1, 50, 175000, DONE),
                ),
            ),
        ]
        for case, segments in rows:
            with self.subTest(case=case):
                # Act
                budget = describe_role_budget(segments, SHIPPED_BUDGET, LATEST_RECORDED)

                # Assert
                self.assertEqual(budget.applied, 75)

    def test_should_measure_only_the_segments_at_the_current_digests(self):
        # Arrange
        segments = (
            _create_segment("r0", 1, 90, 900000, DONE, role_digest=OLDER_ROLE_DIGEST),
            *_create_three_restarted_runs(restart_tokens=200000),
        )

        # Act
        budget = describe_role_budget(segments, SHIPPED_BUDGET, LATEST_RECORDED)

        # Assert
        self.assertEqual(budget.segments, 6)
        self.assertEqual(budget.applied, 63)

    def test_should_take_the_digests_of_the_launch_over_the_latest_recorded(self):
        # Arrange
        segments = _create_three_restarted_runs(restart_tokens=200000)
        launch = CurrentDigests(role=OLDER_ROLE_DIGEST, procedures={"build-task": PROCEDURE_DIGEST})

        # Act
        budget = describe_role_budget(segments, SHIPPED_BUDGET, launch)

        # Assert
        self.assertEqual(budget.segments, 0)
        self.assertEqual(budget.applied, 75)

    def test_should_compute_no_cap_from_segments_whose_steps_cost_no_more_as_they_grow(self):
        # Arrange
        flat = (
            _create_segment("r1", 1, 10, 10000, TURN_LIMIT),
            _create_segment("r1", 2, 20, 20000, DONE, tokens_to_first_edit=200000),
            _create_segment("r2", 1, 30, 30000, TURN_LIMIT),
            _create_segment("r2", 2, 40, 40000, DONE, tokens_to_first_edit=200000),
            _create_segment("r3", 1, 50, 50000, TURN_LIMIT),
            _create_segment("r3", 2, 10, 10000, DONE, tokens_to_first_edit=200000),
        )
        same_length = (
            _create_segment("r1", 1, 20, 40000, DONE),
            _create_segment("r2", 1, 20, 40000, DONE),
            _create_segment("r3", 1, 20, 40000, DONE),
            _create_segment("r4", 1, 20, 40000, DONE),
            _create_segment("r5", 1, 20, 40000, DONE),
        )
        no_restart = (
            _create_segment("r1", 1, 10, 15000, DONE),
            _create_segment("r2", 1, 20, 40000, DONE),
            _create_segment("r3", 1, 30, 75000, DONE),
            _create_segment("r4", 1, 40, 120000, DONE),
            _create_segment("r5", 1, 50, 175000, DONE),
        )
        for case, segments in [("no growth", flat), ("one length", same_length), ("no restart", no_restart)]:
            with self.subTest(case=case):
                # Act
                budget = describe_role_budget(segments, SHIPPED_BUDGET, LATEST_RECORDED)

                # Assert
                self.assertIsNone(budget.computed)
                self.assertEqual(budget.applied, 75)

    def test_should_measure_no_segment_recorded_before_the_digests(self):
        # Arrange
        segments = (
            _create_segment("r1", 1, 10, 15000, TURN_LIMIT, role_digest=None),
            _create_segment("r1", 2, 20, 40000, DONE, role_digest=None, tokens_to_first_edit=200000),
        )

        # Act
        budget = describe_role_budget(segments, SHIPPED_BUDGET, LATEST_RECORDED)

        # Assert
        self.assertEqual(budget.segments, 0)

    def test_should_count_as_restarts_only_the_segments_relaunched_after_their_step_cap(self):
        # Arrange
        segments = (
            _create_segment("r1", 1, 10, 15000, DONE, tokens_to_first_edit=90000),
            _create_segment("r2", 1, 30, 75000, "handed_over"),
            _create_segment("r2", 2, 40, 120000, DONE, tokens_to_first_edit=200000),
            _create_segment("r3", 1, 50, 175000, TURN_LIMIT),
            _create_segment("r3", 2, 20, 40000, DONE, tokens_to_first_edit=200000),
        )

        # Act
        budget = describe_role_budget(segments, SHIPPED_BUDGET, LATEST_RECORDED)

        # Assert
        self.assertEqual(budget.restarts, 1)
