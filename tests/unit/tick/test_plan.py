import unittest
from datetime import UTC, datetime

from brigade.errors import BrigadeError
from brigade.studies.read_live_study_runs import LiveStudyRun
from brigade.tick.actions import LaunchStudy, LaunchTask, StartWave
from brigade.tick.build_snapshot import (
    LiveRun,
    PlannedRequest,
    ProjectFacts,
    Snapshot,
    StudyFacts,
    TaskFacts,
    WaveFacts,
)
from brigade.tick.plan import plan

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
SHOP = ProjectFacts(name="shop", slots=4)
WAVE_BRANCH = "integration/M1-empty-cart"


def create_wave(tasks: tuple[TaskFacts, ...], states: dict, implemented: tuple[str, ...] = ()) -> WaveFacts:
    return WaveFacts(
        request="shop_1",
        project="shop",
        milestone="M1",
        wave="shop_w1",
        branch=WAVE_BRANCH,
        tasks=tasks,
        states=states,
        implemented=implemented,
    )


ALONE = (TaskFacts(name="S3"),)
FOLLOWING = (TaskFacts(name="S3", after=("S2",)),)
BLOCKED = (TaskFacts(name="S3", blocked_by=("OPEN_QUESTION.Undecided",)),)


LAUNCH_S3 = LaunchTask(request="shop_1", project="shop", milestone="M1", wave="shop_w1", branch=WAVE_BRANCH, task="S3")
LAUNCH_S9 = LaunchTask(request="shop_1", project="shop", milestone="M1", wave="shop_w1", branch=WAVE_BRANCH, task="S9")
LAUNCH_S10 = LaunchTask(
    request="shop_1", project="shop", milestone="M1", wave="shop_w1", branch=WAVE_BRANCH, task="S10"
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
            ("parked", ALONE, {"S3": "parked"}, (), ()),
            ("after a task merged in the wave", FOLLOWING, {"S2": "merged"}, (), (LAUNCH_S3,)),
            ("after a task implemented in the corpus", FOLLOWING, {}, ("S2",), (LAUNCH_S3,)),
            ("after a task still running", FOLLOWING, {"S2": "running"}, (), ()),
            ("after a task neither merged nor implemented", FOLLOWING, {}, (), ()),
            ("blocked by a live question", BLOCKED, {}, (), ()),
            ("implemented at the branch of the wave with no state", ALONE, {}, ("S3",), ()),
        ]:
            with self.subTest(case=case):
                # Arrange
                snapshot = Snapshot(now=NOW, waves=(create_wave(tasks, states, implemented),), projects=(SHOP,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)


class PlanSlotsTest(unittest.TestCase):
    def test_should_launch_within_the_slots_left_by_the_live_build_runs_in_the_order_of_the_numbers(self):
        # Arrange
        project = ProjectFacts(
            name="shop",
            slots=3,
            live_runs=(
                LiveRun(run="20261006T110000Z-a1b2c3", slot="build"),
                LiveRun(run="20261006T110500Z-d4e5f6", slot="review"),
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
                LiveRun(run="20261006T110000Z-a1b2c3", slot="build"),
                LiveRun(run="20261006T110500Z-d4e5f6", slot="build"),
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
            request="shop_2",
            project="shop",
            milestone="M2",
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
        self.assertEqual(str(raised.exception), "@TASK.Login of the wave M1 carries no number to be ordered by")


class PlanPlannedRequestsTest(unittest.TestCase):
    def test_should_start_a_planned_request_only_under_an_automatic_plan_review(self):
        for plan_review, expected in [
            ("auto", (StartWave(request="shop_2"),)),
            ("ask", ()),
        ]:
            with self.subTest(plan_review=plan_review):
                # Arrange
                planned = PlannedRequest(request="shop_2", project="shop", plan_review=plan_review)
                snapshot = Snapshot(now=NOW, projects=(SHOP,), planned=(planned,))

                # Act
                actions = plan(snapshot)

                # Assert
                self.assertEqual(actions, expected)


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
