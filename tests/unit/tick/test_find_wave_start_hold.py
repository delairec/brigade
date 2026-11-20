import unittest
from datetime import UTC, datetime

from brigade.tick.build_snapshot import MilestoneFacts, ProjectFacts, Snapshot, UncutMilestone
from brigade.tick.find_wave_start_hold import find_wave_start_hold
from brigade.waves.list_candidate_waves import CandidateWave

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
CANDIDATE_OF_M6 = CandidateWave(milestone="M6", tasks=("S7",))
NO_MILESTONE = ()
NOTHING_UNCUT = ()
M6_BEHIND_MAIN = (MilestoneFacts(project="shop", milestone="M6", branch="integration/hardening", behind_main=True),)
M6_REBASED_BY_A_LIVE_RUN = (
    MilestoneFacts(
        project="shop", milestone="M6", branch="integration/hardening", behind_main=True, rebase_run_live=True
    ),
)
M6_UNCUT_WITH_A_TODO_TASK = (UncutMilestone(milestone="M6", branch="integration/hardening", todo=("S7",)),)
M6_UNCUT_AND_UNNAMED = (UncutMilestone(milestone="M6", branch="integration/hardening"),)


class FindWaveStartHoldTest(unittest.TestCase):
    def test_should_name_the_first_cause_that_holds_the_start_of_a_candidate_wave(self):
        for case, wave_start, milestones, uncut_milestones, expected in [
            (
                "a policy asking before a wave start",
                "ask",
                M6_BEHIND_MAIN,
                NOTHING_UNCUT,
                "the policy of @PROJECT.shop asks before a wave start, WAVE_START ask",
            ),
            (
                "a milestone branch rebased in the round",
                "auto",
                M6_BEHIND_MAIN,
                M6_UNCUT_WITH_A_TODO_TASK,
                "the branch of M6 is rebased in this round",
            ),
            (
                "a milestone branch cut in the round",
                "auto",
                NO_MILESTONE,
                M6_UNCUT_WITH_A_TODO_TASK,
                "the branch of M6 is cut in this round",
            ),
            ("a milestone branch rebased by a live run", "auto", M6_REBASED_BY_A_LIVE_RUN, NOTHING_UNCUT, None),
            ("an uncut milestone no task names", "auto", NO_MILESTONE, M6_UNCUT_AND_UNNAMED, None),
        ]:
            with self.subTest(case=case):
                # Arrange
                project = ProjectFacts(
                    name="shop",
                    slots=4,
                    wave_start=wave_start,
                    candidates=(CANDIDATE_OF_M6,),
                    uncut_milestones=uncut_milestones,
                )
                snapshot = Snapshot(now=NOW, projects=(project,), milestones=milestones)

                # Act
                hold = find_wave_start_hold(snapshot, project, CANDIDATE_OF_M6)

                # Assert
                self.assertEqual(hold, expected)


if __name__ == "__main__":
    unittest.main()
