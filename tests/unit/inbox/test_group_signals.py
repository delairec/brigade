import unittest

from brigade.inbox.group_signals import SignalFamily, group_signals
from brigade.inbox.read_inbox import Signal

THREAD_ON_THE_CLI = Signal(
    id="cb358a1",
    fingerprint="rt:101",
    kind="review_thread",
    project="oak",
    count=1,
    age_s=60,
    status="new",
    evidence={"path": "brigade/cli.py", "comment": "see @RULE.kiss"},
)
THREAD_ON_THE_PLANNER = Signal(
    id="698b1db",
    fingerprint="rt:102",
    kind="review_thread",
    project="oak",
    count=1,
    age_s=60,
    status="new",
    evidence={"path": "brigade/tick/plan.py", "comment": "@RULE.kiss again"},
)
OTHER_THREAD_ON_THE_CLI = Signal(
    id="5d0f3a2",
    fingerprint="rt:103",
    kind="review_thread",
    project="oak",
    count=1,
    age_s=60,
    status="new",
    evidence={"path": "brigade/cli.py", "comment": "rename it"},
)
LINT_FAILING_ON_A_PULL_REQUEST = Signal(
    id="0b1c2d3",
    fingerprint="cr:oak:7:lint:abc1234",
    kind="check_run",
    project="oak",
    count=1,
    age_s=60,
    status="new",
    evidence={"name": "lint"},
)
LINT_FAILING_ON_MAIN = Signal(
    id="4e5f6a7",
    fingerprint="cr:oak:main:lint:def5678",
    kind="check_run",
    project="oak",
    count=1,
    age_s=60,
    status="new",
    evidence={"name": "lint"},
)
NOTE_NAMING_THE_LINT = Signal(
    id="8b9c0d1",
    fingerprint="note:0a1b2c3d4e5f",
    kind="note",
    project=None,
    count=1,
    age_s=60,
    status="new",
    evidence={"text": "the lint is slow", "name": "lint"},
)


class GroupSignalsTest(unittest.TestCase):
    def test_should_group_by_rule_cited_by_file_and_by_check_name_and_leave_the_others_alone(self):
        # Arrange
        signals = (
            THREAD_ON_THE_CLI,
            THREAD_ON_THE_PLANNER,
            OTHER_THREAD_ON_THE_CLI,
            LINT_FAILING_ON_A_PULL_REQUEST,
            LINT_FAILING_ON_MAIN,
            NOTE_NAMING_THE_LINT,
        )

        # Act
        families = group_signals(signals)

        # Assert
        self.assertEqual(
            families,
            (
                SignalFamily(by="rule", key="@RULE.kiss", signals=(THREAD_ON_THE_CLI, THREAD_ON_THE_PLANNER)),
                SignalFamily(by="file", key="brigade/cli.py", signals=(THREAD_ON_THE_CLI, OTHER_THREAD_ON_THE_CLI)),
                SignalFamily(by="check", key="lint", signals=(LINT_FAILING_ON_A_PULL_REQUEST, LINT_FAILING_ON_MAIN)),
                SignalFamily(by="signal", key="note:0a1b2c3d4e5f", signals=(NOTE_NAMING_THE_LINT,)),
            ),
        )
