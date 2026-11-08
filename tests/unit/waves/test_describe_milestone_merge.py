import unittest
from datetime import UTC, datetime

from brigade.corpus.read_entities import Entity, EntityField
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.order_done import OrderDone
from brigade.waves.describe_milestone_merge import describe_milestone_merge

INSTANT = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
RUN = "20261108T090000Z-a1b2c3"
OTHER_RUN = "20261108T090000Z-d4e5f6"
BRANCH = "integration/empty-cart"
COMMAND = "git -C /srv/shop merge integration/empty-cart"


def _create_project(forge: str = "none") -> Entity:
    return Entity(
        name="shop",
        fields=(EntityField(name="PATH", value="/srv/shop"), EntityField(name="FORGE", value=forge)),
    )


def _record(*events) -> tuple[LedgerEntry, ...]:
    return tuple(LedgerEntry(instant=INSTANT, event=event) for event in events)


CUT = MilestoneBranchCut(project="shop", milestone="M1", branch=BRANCH, login=None)
REPORTED = MilestoneReported(project="shop", milestone="M1", run=RUN, login=None)
REPORT_COMMITTED = OrderDone(project="shop", kind="milestone-report", order=None, run=RUN)
OTHER_RUN_DONE = OrderDone(project="shop", kind="milestone-report", order=None, run=OTHER_RUN)
CLOSED = MilestoneClosed(project="shop", milestone="M1")


class DescribeMilestoneMergeTest(unittest.TestCase):
    def test_should_name_the_command_once_the_report_of_the_milestone_is_committed(self):
        # Arrange
        entries = _record(CUT, REPORTED, REPORT_COMMITTED)

        # Act
        command = describe_milestone_merge(entries, _create_project(), "M1")

        # Assert
        self.assertEqual(command, COMMAND)

    def test_should_name_no_command_before_the_report_is_committed_or_after_the_close_or_on_a_forge(self):
        for case, entries, project in [
            ("no report ran", _record(CUT), _create_project()),
            ("the report still runs", _record(CUT, REPORTED), _create_project()),
            ("another run ended", _record(CUT, REPORTED, OTHER_RUN_DONE), _create_project()),
            ("the milestone closed", _record(CUT, REPORTED, REPORT_COMMITTED, CLOSED), _create_project()),
            ("a project on a forge", _record(CUT, REPORTED, REPORT_COMMITTED), _create_project("github")),
        ]:
            with self.subTest(case=case):
                # Act
                command = describe_milestone_merge(entries, project, "M1")

                # Assert
                self.assertIsNone(command)

    def test_should_name_no_command_for_a_wave_of_no_milestone(self):
        # Act
        command = describe_milestone_merge(_record(CUT, REPORTED, REPORT_COMMITTED), _create_project(), None)

        # Assert
        self.assertIsNone(command)
