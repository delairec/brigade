import dataclasses
import unittest
from datetime import UTC, datetime

from brigade.corpus.read_entities import Entity, EntityField
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.tick.list_blocked_milestone_rebases import (
    BlockedMilestoneRebase,
    MilestoneRebasesReading,
    list_blocked_milestone_rebases,
)
from tests.unit.ledger.create_run_finished import create_run_finished

INSTANT = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)
SHOP = Entity(name="shop", fields=(EntityField(name="PATH", value="/srv/shop"),))
TIDES_CUT = LedgerEntry(
    instant=INSTANT,
    event=MilestoneBranchCut(project="shop", milestone="M9", branch="integration/tides", login="brigade-bot"),
)
TIDES_WORKTREE = "/srv/shop/.brigade/worktrees/integration-tides"
OTHER_WORKTREE = "/srv/shop/.brigade/worktrees/B7"
BLOCKED_MESSAGE = "Keep the guard of plan.py or drop it?\nbrigade-end: blocked"
DEFAULT_WORKTREE_ROOT = None


def create_rebase_run(run: str, worktree: str) -> dict:
    return {"run": run, "slot": "rebase", "project": "shop", "worktree": worktree, "wave": None, "task": None}


def create_finished_entry(run: str, outcome: str) -> LedgerEntry:
    finished = create_run_finished(run, outcome=outcome)
    return LedgerEntry(instant=INSTANT, event=dataclasses.replace(finished, message=BLOCKED_MESSAGE))


class ListBlockedMilestoneRebasesTest(unittest.TestCase):
    def test_should_name_the_milestone_branch_whose_last_rebase_run_ended_blocked_with_its_question(self):
        # Arrange
        reading = MilestoneRebasesReading(
            entries=(TIDES_CUT, create_finished_entry("20261030T080000Z-4eba5e", "blocked")),
            runs=(create_rebase_run("20261030T080000Z-4eba5e", TIDES_WORKTREE),),
            projects=(SHOP,),
            worktree_root=DEFAULT_WORKTREE_ROOT,
        )

        # Act
        blocked = list_blocked_milestone_rebases(reading)

        # Assert
        self.assertEqual(
            blocked,
            (BlockedMilestoneRebase(branch="integration/tides", question="Keep the guard of plan.py or drop it?"),),
        )

    def test_should_name_no_milestone_branch_whose_last_rebase_run_did_not_end_blocked(self):
        for case, runs, entries in [
            ("no rebase run", (), (TIDES_CUT,)),
            (
                "a rebase run delivered",
                (create_rebase_run("20261030T080000Z-4eba5e", TIDES_WORKTREE),),
                (TIDES_CUT, create_finished_entry("20261030T080000Z-4eba5e", "done")),
            ),
            (
                "a blocked run followed by a delivered one",
                (
                    create_rebase_run("20261030T080000Z-4eba5e", TIDES_WORKTREE),
                    create_rebase_run("20261030T090000Z-5fcb6f", TIDES_WORKTREE),
                ),
                (
                    TIDES_CUT,
                    create_finished_entry("20261030T080000Z-4eba5e", "blocked"),
                    create_finished_entry("20261030T090000Z-5fcb6f", "done"),
                ),
            ),
            (
                "a blocked run still running again",
                (
                    create_rebase_run("20261030T080000Z-4eba5e", TIDES_WORKTREE),
                    create_rebase_run("20261030T090000Z-5fcb6f", TIDES_WORKTREE),
                ),
                (TIDES_CUT, create_finished_entry("20261030T080000Z-4eba5e", "blocked")),
            ),
            (
                "a blocked run on the worktree of a task",
                (create_rebase_run("20261030T080000Z-4eba5e", OTHER_WORKTREE),),
                (TIDES_CUT, create_finished_entry("20261030T080000Z-4eba5e", "blocked")),
            ),
            (
                "a blocked run on a milestone branch another project cut",
                (create_rebase_run("20261030T080000Z-4eba5e", TIDES_WORKTREE),),
                (
                    LedgerEntry(
                        instant=INSTANT,
                        event=MilestoneBranchCut(
                            project="depot", milestone="M9", branch="integration/tides", login="brigade-bot"
                        ),
                    ),
                    create_finished_entry("20261030T080000Z-4eba5e", "blocked"),
                ),
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                reading = MilestoneRebasesReading(
                    entries=entries, runs=runs, projects=(SHOP,), worktree_root=DEFAULT_WORKTREE_ROOT
                )

                # Act
                blocked = list_blocked_milestone_rebases(reading)

                # Assert
                self.assertEqual(blocked, ())
