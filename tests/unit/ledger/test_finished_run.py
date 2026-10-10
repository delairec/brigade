import unittest
from dataclasses import replace
from datetime import UTC, datetime

from brigade.ledger.finished_run import FinishedRun, RunMeasure
from brigade.ledger.run_finished import RunFinished

SEGMENT = RunFinished(
    run="20261010T090000Z-b86a01",
    segment=1,
    procedure="awawa-task",
    slot="build",
    role="builder",
    client="claude-code",
    project="tidepool",
    session=None,
    main_steps=None,
    total_steps=None,
    duration_ms=1000,
    usage=None,
    outcome="done",
    error_class=None,
    exit=0,
    wave=None,
    task=None,
    nulls={},
)


def create_segment(**measures) -> RunFinished:
    return replace(SEGMENT, **measures)


def create_run(segments: tuple[RunFinished, ...]) -> FinishedRun:
    return FinishedRun(run="20261010T090000Z-b86a01", finished_at=datetime(2026, 10, 10, tzinfo=UTC), segments=segments)


class FinishedRunTest(unittest.TestCase):
    def test_should_take_the_outcome_of_its_last_segment(self):
        # Arrange
        cut_segment = create_segment(outcome="wall_limit")
        resumed_segment = create_segment(segment=2, outcome="done")
        run = create_run((cut_segment, resumed_segment))

        # Act
        last = run.last

        # Assert
        self.assertEqual(last, resumed_segment)

    def test_should_sum_the_steps_of_its_measured_segments_and_be_partial_when_one_is_not_measured(self):
        rows = [
            ((create_segment(main_steps=40),), RunMeasure(value=40, partial=False)),
            ((create_segment(),), RunMeasure(value=None, partial=False)),
            ((create_segment(main_steps=30), create_segment(main_steps=45)), RunMeasure(value=75, partial=False)),
            ((create_segment(), create_segment(main_steps=30)), RunMeasure(value=30, partial=True)),
            ((create_segment(), create_segment()), RunMeasure(value=None, partial=False)),
        ]
        for segments, expected_measure in rows:
            with self.subTest(segments=segments):
                # Arrange
                run = create_run(segments)

                # Act
                measure = run.main_steps

                # Assert
                self.assertEqual(measure, expected_measure)

    def test_should_sum_the_oversized_output_steps_of_the_segments_reporting_them(self):
        rows = [
            ((create_segment(oversized_output_steps=1),), RunMeasure(value=1, partial=False)),
            (
                (create_segment(oversized_output_steps=1), create_segment(oversized_output_steps=2)),
                RunMeasure(value=3, partial=False),
            ),
            ((create_segment(oversized_output_steps=2), create_segment()), RunMeasure(value=2, partial=True)),
            ((create_segment(), create_segment()), RunMeasure(value=None, partial=False)),
        ]
        for segments, expected_measure in rows:
            with self.subTest(segments=segments):
                # Arrange
                run = create_run(segments)

                # Act
                measure = run.oversized_output_steps

                # Assert
                self.assertEqual(measure, expected_measure)

    def test_should_count_the_steps_to_first_edit_from_the_start_of_the_run(self):
        rows = [
            ((create_segment(main_steps=40, steps_to_first_edit=12),), RunMeasure(value=12, partial=False)),
            ((create_segment(main_steps=40),), RunMeasure(value=None, partial=False)),
            (
                (
                    create_segment(main_steps=40, steps_to_first_edit=12),
                    create_segment(main_steps=30, steps_to_first_edit=5),
                ),
                RunMeasure(value=12, partial=False),
            ),
            (
                (create_segment(main_steps=40), create_segment(main_steps=30, steps_to_first_edit=5)),
                RunMeasure(value=45, partial=False),
            ),
            (
                (create_segment(main_steps=40, steps_to_first_edit=12), create_segment(main_steps=30)),
                RunMeasure(value=12, partial=False),
            ),
            (
                (create_segment(main_steps=40, steps_to_first_edit=12), create_segment()),
                RunMeasure(value=12, partial=False),
            ),
            (
                (create_segment(), create_segment(main_steps=30, steps_to_first_edit=5)),
                RunMeasure(value=5, partial=True),
            ),
        ]
        for segments, expected_measure in rows:
            with self.subTest(segments=segments):
                # Arrange
                run = create_run(segments)

                # Act
                measure = run.steps_to_first_edit

                # Assert
                self.assertEqual(measure, expected_measure)
