import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.list_held_tasks import HeldTask, list_held_tasks
from brigade.waves.read_project_tasks import ProjectTasks

ROOT = Path("/srv/shop")
NO_IMPLEMENTED_TASK = frozenset()
NO_MILESTONE = None
INSTANT = datetime(2026, 11, 9, 1, 35, tzinfo=UTC)
TODO = EntityField(name="STATUS", value="todo")
DIGEST_OF_S3_AS_READ = "21b807323b879dff2247378dd129efd4c59248cf48c93498e31ce3e7709eca31"
S3_AS_READ = Entity(name="S3", fields=(TODO,))
REASON_OF_THE_BLOCKED_RUN = "run r1 blocked: Which forge does the check run against?"
EVERY_TASK_AS_READ = {"S3": S3_AS_READ}


def _create_entry(event) -> LedgerEntry:
    return LedgerEntry(instant=INSTANT, event=event)


def _start_wave(wave: str, digests: dict | None = None, project: str = "shop") -> LedgerEntry:
    recorded = {"S3": DIGEST_OF_S3_AS_READ} if digests is None else digests
    return _create_entry(WaveStarted(wave=wave, project=project, tasks=("S3",), task_digests=recorded))


def _close_wave(wave: str) -> LedgerEntry:
    return _create_entry(WaveClosed(wave=wave, pr=None))


def _park(wave: str, reason: str = REASON_OF_THE_BLOCKED_RUN) -> LedgerEntry:
    return _create_entry(TaskParked(wave=wave, task="S3", reason=reason, blockers=()))


def _read_tasks(by_name: dict, milestone: str | None = NO_MILESTONE) -> ProjectTasks:
    return ProjectTasks(root=ROOT, by_name=by_name, implemented=NO_IMPLEMENTED_TASK, milestone=milestone)


WAVE_PARKED_ON_THE_QUESTION = (_start_wave("shop_w48"), _park("shop_w48"), _close_wave("shop_w48"))


class ListHeldTasksTest(unittest.TestCase):
    def test_should_hold_a_task_its_closed_wave_parked_on_the_question_of_its_run(self):
        # Act
        held = list_held_tasks(WAVE_PARKED_ON_THE_QUESTION, "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(
            held,
            (HeldTask(task="S3", wave="shop_w48", question="Which forge does the check run against?"),),
        )

    def test_should_hold_a_task_its_cancelled_wave_parked_on_the_question_of_its_run(self):
        # Arrange
        cancelled = _create_entry(WaveCancelled(wave="shop_w48", reason="user"))
        entries = (_start_wave("shop_w48"), _park("shop_w48"), cancelled)

        # Act
        held = list_held_tasks(entries, "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(
            held,
            (HeldTask(task="S3", wave="shop_w48", question="Which forge does the check run against?"),),
        )

    def test_should_name_the_first_line_of_a_question_of_several_lines(self):
        # Arrange
        entries = (
            _start_wave("shop_w48"),
            _park("shop_w48", "run r1 blocked: Which forge?\nThe SPEC 5 says none."),
            _close_wave("shop_w48"),
        )

        # Act
        held = list_held_tasks(entries, "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(held[0].question, "Which forge?")

    def test_should_release_a_task_whose_entity_differs_from_the_one_its_run_read(self):
        # Arrange
        amended = {"S3": Entity(name="S3", fields=(TODO, EntityField(name="SPEC", value="the forge is github")))}

        # Act
        held = list_held_tasks(WAVE_PARKED_ON_THE_QUESTION, "shop", _read_tasks(amended))

        # Assert
        self.assertEqual(held, ())

    def test_should_release_a_task_queued_again_by_the_requeue(self):
        # Arrange
        queued = _create_entry(TaskState(wave="shop_w48", task="S3", state="queued", reason="brigade wave requeue"))

        # Act
        held = list_held_tasks((*WAVE_PARKED_ON_THE_QUESTION, queued), "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(held, ())

    def test_should_not_hold_a_task_its_wave_parked_for_any_other_cause(self):
        for reason in ["run dead: r1", "past 2 repair rounds", "blocked", "setup failed"]:
            with self.subTest(reason=reason):
                # Arrange
                entries = (_start_wave("shop_w48"), _park("shop_w48", reason), _close_wave("shop_w48"))

                # Act
                held = list_held_tasks(entries, "shop", _read_tasks(EVERY_TASK_AS_READ))

                # Assert
                self.assertEqual(held, ())

    def test_should_not_hold_a_task_parked_on_its_setup_by_a_task_state(self):
        # Arrange
        parked = _create_entry(TaskState(wave="shop_w48", task="S3", state="parked", reason="setup failed"))
        entries = (_start_wave("shop_w48"), parked, _close_wave("shop_w48"))

        # Act
        held = list_held_tasks(entries, "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(held, ())

    def test_should_judge_a_task_by_the_park_of_its_latest_wave(self):
        # Arrange
        later_wave_parked_on_a_dead_run = (
            _start_wave("shop_w49"),
            _park("shop_w49", "run dead: r2"),
            _close_wave("shop_w49"),
        )

        # Act
        held = list_held_tasks(
            (*WAVE_PARKED_ON_THE_QUESTION, *later_wave_parked_on_a_dead_run), "shop", _read_tasks(EVERY_TASK_AS_READ)
        )

        # Assert
        self.assertEqual(held, ())

    def test_should_not_hold_a_task_parked_in_a_wave_still_open(self):
        # Arrange
        entries = (_start_wave("shop_w48"), _park("shop_w48"))

        # Act
        held = list_held_tasks(entries, "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(held, ())

    def test_should_not_hold_a_task_of_a_wave_that_recorded_no_digest(self):
        # Arrange
        no_digest_recorded = {}
        entries = (_start_wave("shop_w48", no_digest_recorded), _park("shop_w48"), _close_wave("shop_w48"))

        # Act
        held = list_held_tasks(entries, "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(held, ())

    def test_should_not_hold_a_task_of_a_wave_started_before_the_digests_were_recorded(self):
        # Arrange
        started_without_digests = _create_entry(WaveStarted(wave="shop_w48", project="shop", tasks=("S3",)))
        entries = (started_without_digests, _park("shop_w48"), _close_wave("shop_w48"))

        # Act
        held = list_held_tasks(entries, "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(held, ())

    def test_should_not_hold_a_task_no_longer_defined_at_the_branch_read(self):
        # Arrange
        no_task = {}

        # Act
        held = list_held_tasks(WAVE_PARKED_ON_THE_QUESTION, "shop", _read_tasks(no_task))

        # Assert
        self.assertEqual(held, ())

    def test_should_not_hold_a_task_that_is_no_longer_todo(self):
        # Arrange
        implemented = {"S3": Entity(name="S3", fields=(EntityField(name="STATUS", value="implemented"),))}

        # Act
        held = list_held_tasks(WAVE_PARKED_ON_THE_QUESTION, "shop", _read_tasks(implemented))

        # Assert
        self.assertEqual(held, ())

    def test_should_not_hold_a_task_of_another_milestone_than_the_one_read(self):
        # Act
        held = list_held_tasks(WAVE_PARKED_ON_THE_QUESTION, "shop", _read_tasks(EVERY_TASK_AS_READ, "M9"))

        # Assert
        self.assertEqual(held, ())

    def test_should_ignore_the_waves_of_another_project(self):
        # Arrange
        entries = (_start_wave("reef_w1", project="reef"), _park("reef_w1"), _close_wave("reef_w1"))

        # Act
        held = list_held_tasks(entries, "shop", _read_tasks(EVERY_TASK_AS_READ))

        # Assert
        self.assertEqual(held, ())


if __name__ == "__main__":
    unittest.main()
