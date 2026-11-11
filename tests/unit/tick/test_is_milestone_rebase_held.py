import unittest

from brigade.ledger.milestone_rebase_launched import MilestoneRebaseLaunched
from brigade.ledger.milestone_rebased import MilestoneRebased
from brigade.tick.is_milestone_rebase_held import MilestoneHeads, is_milestone_rebase_held

BLOCKED_RUN = "20261109T005056Z-1a10d2"
OTHER_RUN = "20261108T120000Z-9f8e7d"
MAIN_AT_THE_LAUNCH = "70ac4c1f"
BRANCH_AT_THE_LAUNCH = "cad58326"
LAUNCH_OF_THE_BLOCKED_RUN = MilestoneRebaseLaunched(
    project="brigade",
    milestone="M7",
    branch="integration/portability",
    run=BLOCKED_RUN,
    main_head=MAIN_AT_THE_LAUNCH,
    branch_head=BRANCH_AT_THE_LAUNCH,
)
LAUNCH_OF_ANOTHER_RUN = MilestoneRebaseLaunched(
    project="brigade",
    milestone="M7",
    branch="integration/portability",
    run=OTHER_RUN,
    main_head=MAIN_AT_THE_LAUNCH,
    branch_head=BRANCH_AT_THE_LAUNCH,
)
EARLIER_REBASE = MilestoneRebased(
    project="brigade",
    milestone="M7",
    branch="integration/portability",
    before="a811ffdd",
    after=BRANCH_AT_THE_LAUNCH,
    waves=(),
    login=None,
)


class IsMilestoneRebaseHeldTest(unittest.TestCase):
    def test_should_hold_the_blocked_rebase_while_the_heads_its_run_was_launched_on_stand(self):
        for case, events, heads, expected in [
            (
                "both heads stand",
                (EARLIER_REBASE, LAUNCH_OF_THE_BLOCKED_RUN),
                MilestoneHeads(main=MAIN_AT_THE_LAUNCH, branch=BRANCH_AT_THE_LAUNCH),
                True,
            ),
            (
                "the main branch moved since the launch",
                (LAUNCH_OF_THE_BLOCKED_RUN,),
                MilestoneHeads(main="fc03a8ee", branch=BRANCH_AT_THE_LAUNCH),
                False,
            ),
            (
                "the milestone branch moved since the launch",
                (LAUNCH_OF_THE_BLOCKED_RUN,),
                MilestoneHeads(main=MAIN_AT_THE_LAUNCH, branch="08fbe42f"),
                False,
            ),
            (
                "the launch of the run recorded no heads",
                (EARLIER_REBASE,),
                MilestoneHeads(main=MAIN_AT_THE_LAUNCH, branch=BRANCH_AT_THE_LAUNCH),
                False,
            ),
            (
                "only another run of the branch recorded the heads that stand",
                (LAUNCH_OF_ANOTHER_RUN,),
                MilestoneHeads(main=MAIN_AT_THE_LAUNCH, branch=BRANCH_AT_THE_LAUNCH),
                False,
            ),
            (
                "a head that no longer resolves",
                (LAUNCH_OF_THE_BLOCKED_RUN,),
                MilestoneHeads(main=MAIN_AT_THE_LAUNCH, branch=None),
                False,
            ),
        ]:
            with self.subTest(case=case):
                # Act
                held = is_milestone_rebase_held(events, BLOCKED_RUN, heads)

                # Assert
                self.assertIs(held, expected)
