import os
import shutil
import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.runs.prune_runs import PruneOutcome, PruneRequest, prune_runs
from brigade.runs.record_run_pid import record_run_pid
from tests.unit.create_test_paths import create_test_paths
from tests.unit.ledger.create_run_finished import create_run_finished
from tests.unit.runs.write_run_record import write_run_record
from tests.unit.runs.write_run_result import write_run_result

OLDEST = "20261001T090000Z-aaaaaa"
OLDER = "20261002T090000Z-bbbbbb"
DEAD = "20261003T090000Z-cccccc"
RUNNING = "20261004T090000Z-dddddd"
UNREADABLE = "20261005T090000Z-eeeeee"
STUDY = "20261006T090000Z-ffffff"


def settle_at(path: Path, instant: datetime) -> None:
    os.utime(path, (instant.timestamp(), instant.timestamp()))


class PruneRunsTestCase(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)
        self.runs = self.paths.state_root / "runs"
        settle_at(write_run_result(self.runs / OLDEST / "result.json"), datetime(2026, 10, 1, 9, 0, tzinfo=UTC))
        write_run_record(self.runs / OLDEST)
        settle_at(write_run_result(self.runs / OLDER / "result.json"), datetime(2026, 10, 2, 9, 0, tzinfo=UTC))
        write_run_record(self.runs / OLDER)
        settle_at(write_run_record(self.runs / DEAD), datetime(2026, 10, 3, 9, 0, tzinfo=UTC))
        write_run_record(self.runs / RUNNING)
        record_run_pid(self.runs / RUNNING, os.getpid())
        (self.runs / UNREADABLE).mkdir()
        (self.runs / UNREADABLE / "run.json").write_text("not json")
        (self.runs / "notes").mkdir()

    def prune(self, keep: int, **options) -> PruneOutcome:
        return prune_runs(PruneRequest(paths=self.paths, keep=keep, **options))


class PruneRunsBeyondTheKeptOnesTest(PruneRunsTestCase):
    def test_should_remove_the_oldest_settled_runs_and_skip_the_unreadable_one(self):
        # Act
        outcome = self.prune(1)

        # Assert
        self.assertEqual(
            (outcome, sorted(self.runs.iterdir())),
            (
                PruneOutcome(
                    removed=[{"run": OLDEST, "state": "finished"}, {"run": OLDER, "state": "finished"}],
                    skipped=[
                        {
                            "run": UNREADABLE,
                            "reason": f"{self.runs / UNREADABLE / 'run.json'} is not a run record: not a JSON document",
                        }
                    ],
                ),
                [self.runs / DEAD, self.runs / RUNNING, self.runs / UNREADABLE, self.runs / "notes"],
            ),
        )

    def test_should_remove_nothing_on_a_dry_run(self):
        # Act
        outcome = self.prune(1, dry_run=True)

        # Assert
        self.assertEqual(
            (outcome.removed, sorted(self.runs.iterdir())),
            (
                [{"run": OLDEST, "state": "finished"}, {"run": OLDER, "state": "finished"}],
                [
                    self.runs / OLDEST,
                    self.runs / OLDER,
                    self.runs / DEAD,
                    self.runs / RUNNING,
                    self.runs / UNREADABLE,
                    self.runs / "notes",
                ],
            ),
        )

    def test_should_remove_the_runs_settled_before_the_day(self):
        # Act
        outcome = self.prune(10, before=date(2026, 10, 2))

        # Assert
        self.assertEqual(outcome.removed, [{"run": OLDEST, "state": "finished"}])


class PruneRunsResumableTest(PruneRunsTestCase):
    def setUp(self):
        super().setUp()
        append_event(
            self.paths,
            datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
            create_run_finished(OLDEST, outcome="failed", error_class="rate_limit"),
        )

    def test_should_spare_a_run_stopped_by_a_usage_limit(self):
        # Act
        outcome = self.prune(0)

        # Assert
        self.assertEqual(outcome.removed, [{"run": OLDER, "state": "finished"}, {"run": DEAD, "state": "dead"}])

    def test_should_remove_a_run_stopped_by_a_usage_limit_when_asked(self):
        # Act
        outcome = self.prune(0, resumable=True)

        # Assert
        self.assertEqual(outcome.removed[0], {"run": OLDEST, "state": "finished"})


class PruneRunsOfADoneStudyTest(PruneRunsTestCase):
    def test_should_remove_the_directory_of_a_study_the_ledger_records_done(self):
        # Arrange
        (self.runs / STUDY).mkdir()
        append_event(
            self.paths, datetime(2026, 9, 30, 9, 0, tzinfo=UTC), OrderDone(project="tidepool", kind="study", run=STUDY)
        )

        # Act
        outcome = self.prune(3)

        # Assert
        self.assertEqual(outcome.removed, [{"run": STUDY, "state": "finished"}])


class PruneRunsLeftByAnEarlierPruneTest(PruneRunsTestCase):
    def test_should_empty_what_an_earlier_prune_left_removed(self):
        # Arrange
        removed = self.paths.state_root / "runs-removed"
        (removed / OLDEST).mkdir(parents=True)
        (removed / "stray.log").write_text("left over")

        # Act
        self.prune(10)

        # Assert
        self.assertEqual(list(removed.iterdir()), [])

    def test_should_refuse_an_earlier_removal_it_cannot_delete(self):
        # Arrange
        removed = self.paths.state_root / "runs-removed"
        removed.mkdir(parents=True)
        (removed / OLDEST).symlink_to(self.runs / OLDEST, target_is_directory=True)

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            self.prune(10)

        # Assert
        self.assertIn(f"cannot write {removed}/{OLDEST}: ", str(refusal.exception))

    def test_should_refuse_a_removal_place_that_is_a_file(self):
        # Arrange
        (self.paths.state_root / "runs-removed").write_text("not a directory")

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            self.prune(0)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.paths.state_root}/runs-removed: File exists")


class PruneRunsWithoutRunsTest(unittest.TestCase):
    def test_should_remove_nothing(self):
        # Arrange
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)

        # Act
        outcome = prune_runs(PruneRequest(paths=create_test_paths(root), keep=0))

        # Assert
        self.assertEqual(outcome, PruneOutcome(removed=[], skipped=[]))
