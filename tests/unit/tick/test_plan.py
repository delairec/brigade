import dataclasses
import unittest
from datetime import UTC, datetime

from brigade.errors import BrigadeError
from brigade.studies.read_live_study_runs import LiveStudyRun
from brigade.system.pull_request_facts import CheckVerdict, PullRequestFacts
from brigade.system.reset_hour import ResetHour
from brigade.tick.actions import (
    CloseWave,
    CutWaveBranch,
    LaunchStudy,
    LaunchTask,
    LaunchVerification,
    PauseWave,
    RecordTaskState,
    RemoveTaskWorktree,
    ReportWave,
    ResumeTaskRun,
    ResumeWave,
    RunPreflight,
    StartWave,
)
from brigade.tick.build_snapshot import (
    LiveRun,
    ProjectFacts,
    RateLimit,
    RecordedVerdict,
    Snapshot,
    StudyFacts,
    TaskFacts,
    WaveFacts,
    WavePause,
)
from brigade.tick.plan import plan

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
SHOP = ProjectFacts(name="shop", slots=4)
WAVE_BRANCH = "integration/M1-empty-cart"


def create_wave(tasks: tuple[TaskFacts, ...], states: dict, implemented: tuple[str, ...] = ()) -> WaveFacts:
    return WaveFacts(
        project="shop",
        wave="shop_w1",
        branch=WAVE_BRANCH,
        tasks=tasks,
        states=states,
        implemented=implemented,
    )


ALONE = (TaskFacts(name="S3"),)
FOLLOWING = (TaskFacts(name="S3", after=("S2",)),)
BLOCKED = (TaskFacts(name="S3", blocked_by=("OPEN_QUESTION.Undecided",)),)
ALONE_S9 = (TaskFacts(name="S9"),)


LAUNCH_S3 = LaunchTask(project="shop", wave="shop_w1", branch=WAVE_BRANCH, task="S3")
LAUNCH_S9 = LaunchTask(project="shop", wave="shop_w1", branch=WAVE_BRANCH, task="S9")
LAUNCH_S10 = LaunchTask(project="shop", wave="shop_w1", branch=WAVE_BRANCH, task="S10")
REPORT_SHOP_W1 = ReportWave(wave="shop_w1")
PARK_BLOCKED_S3 = RecordTaskState(
    wave="shop_w1", task="S3", state="parked", reason="blocked by @OPEN_QUESTION.Undecided"
)


class PlanTest(unittest.TestCase):
    def test_should_plan_no_action_without_a_wave_or_a_planned_request(self):
        # Arrange
        snapshot = Snapshot(now=NOW)

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, ())


class PlanStartableTasksTest(unittest.TestCase):
    def test_should_launch_a_task_only_when_it_is_startable(self):
        for case, tasks, states, implemented, expected in [
            ("with no state yet", ALONE, {}, (), (LAUNCH_S3,)),
            ("queued", ALONE, {"S3": "queued"}, (), (LAUNCH_S3,)),
            ("already running", ALONE, {"S3": "running"}, (), ()),
            ("with its pull request open", ALONE, {"S3": "pr_open"}, (), ()),
            ("parked", ALONE, {"S3": "parked"}, (), (REPORT_SHOP_W1,)),
            ("after a task merged in the wave", FOLLOWING, {"S2": "merged"}, (), (LAUNCH_S3,)),
            ("after a task implemented in the corpus", FOLLOWING, {}, ("S2",), (LAUNCH_S3,)),
            ("after a task still running", FOLLOWING, {"S2": "running"}, (), ()),
            ("after a task neither merged nor implemented", FOLLOWING, {}, (), ()),
            ("blocked by a live question", BLOCKED, {}, (), (PARK_BLOCKED_S3,)),
            ("implemented at the branch of the wave with no state", ALONE, {}, ("S3",), ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                snapshot = Snapshot(now=NOW, waves=(create_wave(tasks, states, implemented),), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)


WORKTREE_S3 = "/projects/shop/.brigade/worktrees/S3"


HEAD = "0123abc"


def create_pull_request(state: str, verdict: str = "success") -> PullRequestFacts:
    return PullRequestFacts(
        number=42,
        state=state,
        checks=(CheckVerdict(name="tests", verdict=verdict),),
        review=None,
        behind=False,
        head=HEAD,
    )


OPEN = create_pull_request("open")
MERGED = create_pull_request("merged")
CLOSED = create_pull_request("closed")
NO_PULL_REQUEST = None
NO_WORKTREE = None
RECORD_PR_OPEN = RecordTaskState(wave="shop_w1", task="S3", state="pr_open", reason=None)
RECORD_MERGED = RecordTaskState(wave="shop_w1", task="S3", state="merged", reason=None)
RECORD_PARKED = RecordTaskState(wave="shop_w1", task="S3", state="parked", reason="pull request closed")
REMOVE_WORKTREE_S3 = RemoveTaskWorktree(project="shop", task="S3", worktree=WORKTREE_S3)


class PlanFollowedPullRequestsTest(unittest.TestCase):
    def test_should_move_the_task_state_from_the_state_of_its_pull_request(self):
        for case, state, pull_request, expected in [
            ("a running task whose pull request opened", "running", OPEN, (RECORD_PR_OPEN,)),
            ("a running task whose pull request merged", "running", MERGED, (RECORD_MERGED,)),
            ("a running task whose pull request closed", "running", CLOSED, (RECORD_PARKED,)),
            ("a running task with no pull request yet", "running", NO_PULL_REQUEST, ()),
            ("a task whose open pull request is already recorded", "pr_open", OPEN, ()),
            ("a task in review whose pull request merged", "verifying", MERGED, (RECORD_MERGED,)),
            ("a task in fixing whose pull request closed", "fixing", CLOSED, (RECORD_PARKED,)),
            ("a task already merged", "merged", MERGED, (REPORT_SHOP_W1,)),
            ("a task already parked", "parked", CLOSED, (REPORT_SHOP_W1,)),
        ]:
            with self.subTest(case=case):
                # Arrange
                task = TaskFacts(name="S3", pull_request=pull_request, worktree=NO_WORKTREE)
                snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": state}),), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)

    def test_should_remove_the_worktree_of_a_task_once_its_pull_request_is_merged_or_closed(self):
        for case, state, pull_request, expected in [
            ("merged", "merged", MERGED, (REMOVE_WORKTREE_S3, REPORT_SHOP_W1)),
            ("closed", "parked", CLOSED, (REMOVE_WORKTREE_S3, REPORT_SHOP_W1)),
            ("still open", "pr_open", OPEN, ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                task = TaskFacts(name="S3", pull_request=pull_request, worktree=WORKTREE_S3)
                snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": state}),), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)

    def test_should_keep_the_worktree_of_a_merged_task_while_a_run_holds_it(self):
        # Arrange
        holding = ProjectFacts(
            name="shop",
            slots=4,
            live_runs=(LiveRun(run="20261006T110000Z-a1b2c3", slot="build", worktree=WORKTREE_S3),),
        )
        task = TaskFacts(name="S3", pull_request=MERGED, worktree=WORKTREE_S3)
        snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": "merged"}),), projects=(holding,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (REPORT_SHOP_W1,))

    def test_should_record_the_merge_and_remove_the_worktree_in_one_plan(self):
        # Arrange
        task = TaskFacts(name="S3", pull_request=MERGED, worktree=WORKTREE_S3)
        snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": "running"}),), projects=(SHOP,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (RECORD_MERGED, REMOVE_WORKTREE_S3))


PENDING = create_pull_request("open", "pending")
FAILED_CHECK_RUN = create_pull_request("open", "failure")
NO_CHECK_RUN = PullRequestFacts(number=42, state="open", checks=(), review=None, behind=False, head=HEAD)
SHOP_WITHOUT_CHECK_RUNS = ProjectFacts(name="shop", slots=4, awaits_check_runs=False)
OPENED_BY_THE_TASK = 42
OPENED_BY_AN_EARLIER_RUN = 41
NOT_PREFLIGHTED = None
PREFLIGHTED_AT_THE_HEAD = HEAD
PREFLIGHTED_BEFORE_A_PUSH = "fedcba9"
PREFLIGHT_S3 = RunPreflight(project="shop", wave="shop_w1", branch=WAVE_BRANCH, task="S3", pr=42)


class PlanPreflightTest(unittest.TestCase):
    def test_should_run_the_preflight_of_the_pull_request_of_the_task_once_its_check_runs_complete(self):
        for case, state, pull_request, opened, preflighted, project, expected in [
            ("check runs passed", "pr_open", OPEN, OPENED_BY_THE_TASK, NOT_PREFLIGHTED, SHOP, (PREFLIGHT_S3,)),
            (
                "a check run failed",
                "pr_open",
                FAILED_CHECK_RUN,
                OPENED_BY_THE_TASK,
                NOT_PREFLIGHTED,
                SHOP,
                (PREFLIGHT_S3,),
            ),
            ("a check run pending", "pr_open", PENDING, OPENED_BY_THE_TASK, NOT_PREFLIGHTED, SHOP, ()),
            ("no check run yet", "pr_open", NO_CHECK_RUN, OPENED_BY_THE_TASK, NOT_PREFLIGHTED, SHOP, ()),
            (
                "no check run in a project without continuous integration",
                "pr_open",
                NO_CHECK_RUN,
                OPENED_BY_THE_TASK,
                NOT_PREFLIGHTED,
                SHOP_WITHOUT_CHECK_RUNS,
                (PREFLIGHT_S3,),
            ),
            ("a head pushed", "pr_open", OPEN, OPENED_BY_THE_TASK, PREFLIGHTED_BEFORE_A_PUSH, SHOP, (PREFLIGHT_S3,)),
            ("a head preflighted", "pr_open", OPEN, OPENED_BY_THE_TASK, PREFLIGHTED_AT_THE_HEAD, SHOP, ()),
            ("another pull request", "pr_open", OPEN, OPENED_BY_AN_EARLIER_RUN, NOT_PREFLIGHTED, SHOP, ()),
            ("a task in review", "verifying", OPEN, OPENED_BY_THE_TASK, PREFLIGHTED_AT_THE_HEAD, SHOP, ()),
            ("a pull request merged", "pr_open", MERGED, OPENED_BY_THE_TASK, NOT_PREFLIGHTED, SHOP, (RECORD_MERGED,)),
        ]:
            with self.subTest(case=case):
                # Arrange
                task = TaskFacts(
                    name="S3", pull_request=pull_request, opened_pull_request=opened, preflighted_head=preflighted
                )
                snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": state}),), projects=(project,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)


NO_VERDICT = None
PASS_AT_THE_HEAD = RecordedVerdict(head=HEAD, verdict="pass")
CHANGES_AT_THE_HEAD = RecordedVerdict(head=HEAD, verdict="changes")
PASS_BEFORE_A_PUSH = RecordedVerdict(head="fedcba9", verdict="pass")
NOT_REVIEWED = None
REVIEWED_AT_THE_HEAD = HEAD
REVIEWED_BEFORE_A_PUSH = "fedcba9"
DISPOSABLE_WORKTREE = "/state/brigade/runs/20261006T110000Z-d4e5f6/worktree"
VERIFY_S3 = LaunchVerification(project="shop", wave="shop_w1", task="S3", pr=42, worktree=WORKTREE_S3)
RECORD_VERIFIED = RecordTaskState(wave="shop_w1", task="S3", state="verified", reason=None)
RECORD_CHANGES_REQUESTED = RecordTaskState(wave="shop_w1", task="S3", state="changes_requested", reason=None)


class PlanVerificationTest(unittest.TestCase):
    def test_should_verify_the_head_of_the_pull_request_of_a_task_in_verifying(self):
        for case, state, verdict, reviewed, worktree, expected in [
            ("with no verdict yet", "verifying", NO_VERDICT, NOT_REVIEWED, WORKTREE_S3, (VERIFY_S3,)),
            (
                "passed at the head",
                "verifying",
                PASS_AT_THE_HEAD,
                REVIEWED_AT_THE_HEAD,
                WORKTREE_S3,
                (RECORD_VERIFIED,),
            ),
            (
                "with changes asked at the head",
                "verifying",
                CHANGES_AT_THE_HEAD,
                REVIEWED_AT_THE_HEAD,
                WORKTREE_S3,
                (RECORD_CHANGES_REQUESTED,),
            ),
            ("reviewed at the head without a verdict", "verifying", NO_VERDICT, REVIEWED_AT_THE_HEAD, WORKTREE_S3, ()),
            ("without its worktree", "verifying", NO_VERDICT, NOT_REVIEWED, NO_WORKTREE, ()),
            ("not yet preflighted", "pr_open", NO_VERDICT, NOT_REVIEWED, WORKTREE_S3, ()),
            ("already verified", "verified", PASS_AT_THE_HEAD, REVIEWED_AT_THE_HEAD, WORKTREE_S3, ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                task = TaskFacts(
                    name="S3",
                    pull_request=OPEN,
                    worktree=worktree,
                    preflighted_head=PREFLIGHTED_AT_THE_HEAD,
                    verdict=verdict,
                    reviewed_head=reviewed,
                )
                snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": state}),), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)

    def test_should_move_back_to_pr_open_a_task_in_verifying_whose_head_moved_since_its_preflight(self):
        for case, verdict, reviewed in [
            ("passed before a push", PASS_BEFORE_A_PUSH, REVIEWED_BEFORE_A_PUSH),
            ("reviewed without a verdict before a push", NO_VERDICT, REVIEWED_BEFORE_A_PUSH),
            ("pushed during its first review run", NO_VERDICT, NOT_REVIEWED),
        ]:
            with self.subTest(case=case):
                # Arrange
                task = TaskFacts(
                    name="S3",
                    pull_request=OPEN,
                    worktree=WORKTREE_S3,
                    preflighted_head=PREFLIGHTED_BEFORE_A_PUSH,
                    verdict=verdict,
                    reviewed_head=reviewed,
                )
                snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": "verifying"}),), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, (RECORD_PR_OPEN,))

    def test_should_start_no_verification_while_a_run_of_the_task_is_live(self):
        for case, live in [
            (
                "a build run holding its worktree",
                LiveRun(run="20261006T110000Z-a1b2c3", slot="build", worktree=WORKTREE_S3),
            ),
            (
                "a review run of the task in a disposable worktree",
                LiveRun(
                    run="20261006T110000Z-d4e5f6",
                    slot="review",
                    worktree=DISPOSABLE_WORKTREE,
                    wave="shop_w1",
                    task="S3",
                ),
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                holding = ProjectFacts(name="shop", slots=4, live_runs=(live,))
                task = TaskFacts(
                    name="S3", pull_request=OPEN, worktree=WORKTREE_S3, preflighted_head=PREFLIGHTED_AT_THE_HEAD
                )
                snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": "verifying"}),), projects=(holding,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, ())

    def test_should_record_the_merge_of_a_task_in_verifying_rather_than_its_verdict(self):
        # Arrange
        task = TaskFacts(name="S3", pull_request=MERGED, worktree=WORKTREE_S3, verdict=PASS_AT_THE_HEAD)
        snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": "verifying"}),), projects=(SHOP,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (RECORD_MERGED, REMOVE_WORKTREE_S3))

    def test_should_verify_a_task_while_a_review_run_of_another_task_is_live(self):
        # Arrange
        other = LiveRun(
            run="20261006T110000Z-d4e5f6", slot="review", worktree=DISPOSABLE_WORKTREE, wave="shop_w1", task="S9"
        )
        holding = ProjectFacts(name="shop", slots=4, live_runs=(other,))
        task = TaskFacts(name="S3", pull_request=OPEN, worktree=WORKTREE_S3, preflighted_head=PREFLIGHTED_AT_THE_HEAD)
        snapshot = Snapshot(now=NOW, waves=(create_wave((task,), {"S3": "verifying"}),), projects=(holding,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (VERIFY_S3,))


class PlanSlotsTest(unittest.TestCase):
    def test_should_launch_within_the_slots_left_by_the_live_build_runs_in_the_order_of_the_numbers(self):
        # Arrange
        project = ProjectFacts(
            name="shop",
            slots=3,
            live_runs=(
                LiveRun(run="20261006T110000Z-a1b2c3", slot="build", worktree="/projects/shop/.brigade/worktrees/S1"),
                LiveRun(run="20261006T110500Z-d4e5f6", slot="review", worktree="/projects/shop"),
            ),
        )
        tasks = (TaskFacts(name="S10"), TaskFacts(name="S9"), TaskFacts(name="S11"))
        snapshot = Snapshot(now=NOW, waves=(create_wave(tasks, {}),), projects=(project,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (LAUNCH_S9, LAUNCH_S10))

    def test_should_launch_nothing_in_a_project_whose_live_build_runs_exceed_its_slots(self):
        # Arrange
        project = ProjectFacts(
            name="shop",
            slots=1,
            live_runs=(
                LiveRun(run="20261006T110000Z-a1b2c3", slot="build", worktree="/projects/shop/.brigade/worktrees/S1"),
                LiveRun(run="20261006T110500Z-d4e5f6", slot="build", worktree="/projects/shop/.brigade/worktrees/S2"),
            ),
        )
        snapshot = Snapshot(now=NOW, waves=(create_wave(ALONE, {}),), projects=(project,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, ())

    def test_should_share_the_slots_of_a_project_between_its_waves(self):
        # Arrange
        project = ProjectFacts(name="shop", slots=1)
        first = create_wave((TaskFacts(name="S3"),), {})
        second = WaveFacts(
            project="shop",
            wave="shop_w2",
            branch="integration/M2-total",
            tasks=(TaskFacts(name="S7"),),
        )
        snapshot = Snapshot(now=NOW, waves=(first, second), projects=(project,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (LAUNCH_S3,))


class PlanTaskOrderTest(unittest.TestCase):
    def test_should_refuse_a_startable_task_whose_name_carries_no_number_to_order_it_by(self):
        # Arrange
        snapshot = Snapshot(now=NOW, waves=(create_wave((TaskFacts(name="Login"),), {}),), projects=(SHOP,))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            plan(snapshot)

        # Assert
        self.assertEqual(str(raised.exception), "@TASK.Login of the wave shop_w1 carries no number to be ordered by")


def create_study(
    *,
    name: str = "weekly",
    slot: str = "report",
    every: str | None = "1h",
    status: str = "active",
    last_started: datetime | None = None,
    parked: bool = False,
) -> StudyFacts:
    return StudyFacts(name=name, slot=slot, every=every, status=status, last_started=last_started, parked=parked)


TWO_HOURS_AGO = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)
HALF_AN_HOUR_AGO = datetime(2026, 10, 6, 11, 30, tzinfo=UTC)
LAUNCH_WEEKLY = LaunchStudy(study="weekly")
LAUNCH_MONTHLY = LaunchStudy(study="monthly")
LAUNCH_TREES = LaunchStudy(study="trees")
LIVE_MONTHLY = LiveStudyRun(study="monthly", run="20261006T110000Z-a1b2c3")
LIVE_TREES = LiveStudyRun(study="trees", run="20261006T110500Z-d4e5f6")


class PlanDueStudiesTest(unittest.TestCase):
    def test_should_launch_a_study_only_when_it_is_due(self):
        for case, study, expected in [
            ("never ran", create_study(), (LAUNCH_WEEKLY,)),
            ("started before its schedule passed", create_study(last_started=TWO_HOURS_AGO), (LAUNCH_WEEKLY,)),
            ("started within its schedule", create_study(last_started=HALF_AN_HOUR_AGO), ()),
            ("run on demand", create_study(every=None), ()),
            ("paused", create_study(status="paused"), ()),
            ("archived", create_study(status="archived"), ()),
            ("parked", create_study(last_started=TWO_HOURS_AGO, parked=True), ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                snapshot = Snapshot(now=NOW, studies=(study,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)

    def test_should_launch_no_study_while_a_run_of_it_is_live(self):
        # Arrange
        live_weekly = (LiveStudyRun(study="weekly", run="20261006T110000Z-a1b2c3"),)
        snapshot = Snapshot(now=NOW, studies=(create_study(),), live_study_runs=live_weekly)

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, ())

    def test_should_refuse_a_schedule_of_another_form_naming_the_study(self):
        # Arrange
        snapshot = Snapshot(now=NOW, studies=(create_study(every="1d"),))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            plan(snapshot)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "@STUDY.weekly: the schedule 1d is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun",
        )


class PlanStudyRunsTest(unittest.TestCase):
    def test_should_launch_the_judging_studies_within_the_study_runs_in_the_order_of_their_names(self):
        # Arrange
        studies = (create_study(name="weekly"), create_study(name="monthly"))
        snapshot = Snapshot(now=NOW, studies=studies, study_runs=1)

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (LAUNCH_MONTHLY,))

    def test_should_count_the_live_runs_of_judging_studies_against_the_study_runs(self):
        for case, live_study_runs, expected in [
            ("a judging study live", (LIVE_MONTHLY,), ()),
            ("a scan live", (LIVE_TREES,), (LAUNCH_WEEKLY,)),
        ]:
            with self.subTest(case=case):
                # Arrange
                studies = (
                    create_study(name="weekly"),
                    create_study(name="monthly", every=None),
                    create_study(name="trees", slot="none", every=None),
                )
                snapshot = Snapshot(now=NOW, studies=studies, live_study_runs=live_study_runs, study_runs=1)

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)

    def test_should_launch_a_scan_beyond_the_study_runs(self):
        # Arrange
        studies = (create_study(name="monthly", every=None), create_study(name="trees", slot="none"))
        snapshot = Snapshot(now=NOW, studies=studies, live_study_runs=(LIVE_MONTHLY,), study_runs=1)

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (LAUNCH_TREES,))

    def test_should_count_the_live_run_of_a_study_the_corpus_no_longer_holds_as_judging(self):
        # Arrange
        snapshot = Snapshot(now=NOW, studies=(create_study(),), live_study_runs=(LIVE_MONTHLY,), study_runs=1)

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, ())


CAFE_WAVE = WaveFacts(project="cafe", wave="cafe_w1", branch="integration/M2-menu")
CAFE = ProjectFacts(name="cafe", slots=4)
RATE_LIMITED_UNTIL_15 = (TaskFacts(name="S3", rate_limit=RateLimit(reset=ResetHour(hour="15:00", timezone="UTC"))),)
RATE_LIMITED_WITHOUT_RESET = (TaskFacts(name="S3", rate_limit=RateLimit(reset=None)),)
STOPPED_RUN = "20261006T113000Z-a1b2c3"
STOPPED_S3 = (TaskFacts(name="S3", stopped_run=STOPPED_RUN),)
PAUSED_S3 = RecordTaskState(wave="shop_w1", task="S3", state="paused:quota", reason=None)
QUOTA_UNTIL_13 = WavePause(reason="quota", resume_at=datetime(2026, 10, 6, 13, 0, tzinfo=UTC))
QUOTA_UNTIL_12 = WavePause(reason="quota", resume_at=NOW)
FORGE_ACCOUNT = WavePause(reason="forge_account", resume_at=None)


class PlanQuotaPauseTest(unittest.TestCase):
    def test_should_pause_every_running_wave_until_the_reset_and_the_rate_limited_task_on_the_quota(self):
        for case, tasks, resume_at in [
            ("with a reset", RATE_LIMITED_UNTIL_15, "2026-10-06T15:00:00Z"),
            ("without a reset", RATE_LIMITED_WITHOUT_RESET, "2026-10-06T12:30:00Z"),
        ]:
            with self.subTest(case=case):
                # Arrange
                snapshot = Snapshot(
                    now=NOW,
                    waves=(create_wave(tasks + ALONE_S9, {"S3": "running"}), CAFE_WAVE),
                    projects=(SHOP, CAFE),
                    rate_limits=(tasks[0].rate_limit,),
                )

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(
                    actions,
                    (
                        PauseWave(wave="shop_w1", reason="quota", resume_at=resume_at),
                        PauseWave(wave="cafe_w1", reason="quota", resume_at=resume_at),
                        PAUSED_S3,
                    ),
                )

    def test_should_pause_every_running_wave_on_a_rate_limit_of_a_run_of_no_task(self):
        # Arrange
        snapshot = Snapshot(
            now=NOW,
            waves=(create_wave(ALONE, {}), CAFE_WAVE),
            projects=(SHOP, CAFE),
            rate_limits=(RateLimit(reset=ResetHour(hour="15:00", timezone="UTC")),),
        )

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(
            actions,
            (
                PauseWave(wave="shop_w1", reason="quota", resume_at="2026-10-06T15:00:00Z"),
                PauseWave(wave="cafe_w1", reason="quota", resume_at="2026-10-06T15:00:00Z"),
            ),
        )

    def test_should_move_a_rate_limited_task_to_paused_quota_without_pausing_its_wave_once_the_rate_limit_is_over(
        self,
    ):
        # Arrange
        snapshot = Snapshot(now=NOW, waves=(create_wave(RATE_LIMITED_UNTIL_15, {"S3": "running"}),), projects=(SHOP,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (PAUSED_S3,))

    def test_should_pause_a_wave_started_during_a_quota_pause_until_the_same_resume_at(self):
        for case, rate_limits in [
            ("with no rate limit in force", ()),
            ("with a rate limit in force", (RateLimit(reset=ResetHour(hour="15:00", timezone="UTC")),)),
        ]:
            with self.subTest(case=case):
                # Arrange
                cafe = dataclasses.replace(CAFE_WAVE, pause=QUOTA_UNTIL_13)
                snapshot = Snapshot(
                    now=NOW, waves=(create_wave(ALONE, {}), cafe), projects=(SHOP, CAFE), rate_limits=rate_limits
                )

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(
                    actions, (PauseWave(wave="shop_w1", reason="quota", resume_at="2026-10-06T13:00:00Z"),)
                )

    def test_should_pause_no_wave_started_once_the_quota_pause_is_over(self):
        # Arrange
        cafe = dataclasses.replace(CAFE_WAVE, pause=QUOTA_UNTIL_12)
        snapshot = Snapshot(now=NOW, waves=(create_wave(ALONE, {}), cafe), projects=(SHOP, CAFE))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (ResumeWave(wave="cafe_w1", reason="quota"), LAUNCH_S3))

    def test_should_move_a_rate_limited_task_of_a_wave_already_paused_without_pausing_it_again(self):
        # Arrange
        wave = dataclasses.replace(create_wave(RATE_LIMITED_UNTIL_15, {"S3": "running"}), pause=QUOTA_UNTIL_13)
        snapshot = Snapshot(now=NOW, waves=(wave,), projects=(SHOP,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (PAUSED_S3,))

    def test_should_launch_no_task_of_a_paused_wave(self):
        for case, pause in [("on the quota", QUOTA_UNTIL_13), ("on the forge account", FORGE_ACCOUNT)]:
            with self.subTest(case=case):
                # Arrange
                wave = dataclasses.replace(create_wave(ALONE, {}), pause=pause)
                snapshot = Snapshot(now=NOW, waves=(wave,), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, ())


class PlanQuotaResumeTest(unittest.TestCase):
    def test_should_resume_a_wave_paused_on_the_quota_and_its_paused_runs_once_resume_at_is_reached(self):
        # Arrange
        wave = dataclasses.replace(
            create_wave(STOPPED_S3 + ALONE_S9, {"S3": "paused:quota", "S9": "running"}), pause=QUOTA_UNTIL_12
        )
        snapshot = Snapshot(now=NOW, waves=(wave,), projects=(SHOP,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(
            actions,
            (
                ResumeWave(wave="shop_w1", reason="quota"),
                ResumeTaskRun(wave="shop_w1", task="S3", run=STOPPED_RUN),
            ),
        )

    def test_should_keep_a_wave_paused_before_its_resume_at_or_on_the_forge_account(self):
        for case, pause in [("before resume_at", QUOTA_UNTIL_13), ("on the forge account", FORGE_ACCOUNT)]:
            with self.subTest(case=case):
                # Arrange
                wave = dataclasses.replace(create_wave(STOPPED_S3, {"S3": "paused:quota"}), pause=pause)
                snapshot = Snapshot(now=NOW, waves=(wave,), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, ())

    def test_should_resume_the_paused_runs_of_a_wave_the_user_resumed(self):
        # Arrange
        snapshot = Snapshot(now=NOW, waves=(create_wave(STOPPED_S3, {"S3": "paused:quota"}),), projects=(SHOP,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (ResumeTaskRun(wave="shop_w1", task="S3", run=STOPPED_RUN),))


class PlanForgeAccountPauseTest(unittest.TestCase):
    def test_should_pause_every_running_wave_not_paused_on_an_unavailable_forge_account(self):
        # Arrange
        shop = dataclasses.replace(create_wave(ALONE, {}), forge_account_unavailable=True)
        cafe = dataclasses.replace(CAFE_WAVE, forge_account_unavailable=True, pause=FORGE_ACCOUNT)
        snapshot = Snapshot(now=NOW, waves=(shop, cafe), projects=(SHOP, CAFE))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (PauseWave(wave="shop_w1", reason="forge_account", resume_at=None),))


PROJECT_WITH_CANDIDATES = ProjectFacts(name="shop", slots=4, candidates=("S7", "S8"))
PROJECT_ASKING_WITH_CANDIDATES = ProjectFacts(name="shop", slots=4, wave_start="ask", candidates=("S7", "S8"))
PROJECT_WITHOUT_CANDIDATES = ProjectFacts(name="shop", slots=4)


class PlanWaveStartTest(unittest.TestCase):
    def test_should_start_a_wave_only_under_auto_and_with_a_candidate(self):
        for case, project, expected in [
            ("under auto with candidates", PROJECT_WITH_CANDIDATES, (StartWave(project="shop"),)),
            ("under ask with candidates", PROJECT_ASKING_WITH_CANDIDATES, ()),
            ("under auto without candidates", PROJECT_WITHOUT_CANDIDATES, ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                snapshot = Snapshot(now=NOW, projects=(project,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)


class PlanMissingWaveBranchTest(unittest.TestCase):
    def test_should_cut_the_missing_branch_of_an_open_wave_and_launch_nothing_in_it(self):
        # Arrange
        wave = WaveFacts(project="shop", wave="shop_w1", branch=WAVE_BRANCH, branch_missing=True)
        snapshot = Snapshot(now=NOW, waves=(wave,), projects=(SHOP,))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, (CutWaveBranch(project="shop", wave="shop_w1", branch=WAVE_BRANCH),))


BLOCKED_TWICE = (TaskFacts(name="S3", blocked_by=("OPEN_QUESTION.Undecided", "OPEN_QUESTION.Unsettled")),)


class PlanBlockedTaskParkingTest(unittest.TestCase):
    def test_should_park_a_queued_task_a_live_blocker_cites(self):
        for case, tasks, states, expected in [
            (
                "with no state yet",
                BLOCKED,
                {},
                (
                    RecordTaskState(
                        wave="shop_w1", task="S3", state="parked", reason="blocked by @OPEN_QUESTION.Undecided"
                    ),
                ),
            ),
            (
                "queued",
                BLOCKED,
                {"S3": "queued"},
                (
                    RecordTaskState(
                        wave="shop_w1", task="S3", state="parked", reason="blocked by @OPEN_QUESTION.Undecided"
                    ),
                ),
            ),
            (
                "cited by two blockers",
                BLOCKED_TWICE,
                {},
                (
                    RecordTaskState(
                        wave="shop_w1",
                        task="S3",
                        state="parked",
                        reason="blocked by @OPEN_QUESTION.Undecided, @OPEN_QUESTION.Unsettled",
                    ),
                ),
            ),
            ("already running", BLOCKED, {"S3": "running"}, ()),
            ("with its pull request open", BLOCKED, {"S3": "pr_open"}, ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                snapshot = Snapshot(now=NOW, waves=(create_wave(tasks, states),), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)


TWO_TASKS = (TaskFacts(name="S3"), TaskFacts(name="S4"))


class PlanWaveReportTest(unittest.TestCase):
    def test_should_report_a_wave_once_every_task_is_merged_or_parked(self):
        for case, states, reported, expected in [
            ("every task merged or parked", {"S3": "merged", "S4": "parked"}, False, (ReportWave(wave="shop_w1"),)),
            (
                "a task still queued",
                {"S3": "merged", "S4": "queued"},
                False,
                (LaunchTask(project="shop", wave="shop_w1", branch=WAVE_BRANCH, task="S4"),),
            ),
            ("a task still running", {"S3": "merged", "S4": "running"}, False, ()),
            ("a task with its pull request open", {"S3": "parked", "S4": "pr_open"}, False, ()),
            ("already reported", {"S3": "merged", "S4": "parked"}, True, ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                wave = dataclasses.replace(create_wave(TWO_TASKS, states), reported=reported)
                snapshot = Snapshot(now=NOW, waves=(wave,), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)


INTEGRATION_MERGED = PullRequestFacts(number=77, state="merged", checks=(), review=None, behind=False)
INTEGRATION_OPEN = PullRequestFacts(number=77, state="open", checks=(), review=None, behind=False)
NO_INTEGRATION_PULL_REQUEST = None


class PlanWaveCloseTest(unittest.TestCase):
    def test_should_close_a_wave_once_its_integration_pull_request_is_merged(self):
        for case, integration, expected in [
            ("merged", INTEGRATION_MERGED, (CloseWave(wave="shop_w1", pr=77),)),
            ("still open", INTEGRATION_OPEN, ()),
            ("not opened yet", NO_INTEGRATION_PULL_REQUEST, ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                wave = dataclasses.replace(
                    create_wave(TWO_TASKS, {"S3": "running", "S4": "running"}), integration_pull_request=integration
                )
                snapshot = Snapshot(now=NOW, waves=(wave,), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)
