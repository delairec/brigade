import unittest
from datetime import UTC, datetime

from brigade.studies.read_live_study_runs import LiveStudyRun
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.system.reset_hour import ResetHour
from brigade.tick.build_snapshot import (
    BlockedRun,
    MergedWave,
    MilestoneFacts,
    PreflightFailure,
    ProjectFacts,
    RateLimit,
    RecordedVerdict,
    Snapshot,
    StudyFacts,
    TaskFacts,
    WaveFacts,
)
from brigade.waves.list_candidate_waves import CandidateWave
from brigade.waves.read_wave_pause import WavePause


class SnapshotTest(unittest.TestCase):
    def test_should_carry_now_as_an_utc_instant_in_its_document(self):
        # Arrange
        snapshot = Snapshot(now=datetime(2026, 10, 6, 12, 0, 7, 250000, tzinfo=UTC))

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "now": "2026-10-06T12:00:07Z",
                "waves": [],
                "projects": [],
                "studies": [],
                "live_study_runs": [],
                "study_runs": 2,
                "rate_limits": [],
                "milestones": [],
            },
        )

    def test_should_carry_the_rate_limits_in_force_in_its_document(self):
        # Arrange
        rate_limits = (RateLimit(reset=ResetHour(hour="7pm", timezone="Europe/Paris")), RateLimit(reset=None))
        snapshot = Snapshot(now=datetime(2026, 10, 18, 12, 0, tzinfo=UTC), rate_limits=rate_limits)

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            document["rate_limits"], [{"reset": {"hour": "7pm", "timezone": "Europe/Paris"}}, {"reset": None}]
        )

    def test_should_carry_the_milestones_and_their_pull_request_in_its_document(self):
        # Arrange
        milestones = (
            MilestoneFacts(
                project="shop",
                milestone="M4",
                branch="integration/tides",
                merged_waves=(MergedWave(wave="shop_w1", pr=77),),
                open_waves=("shop_w3",),
                todo=("S5",),
            ),
            MilestoneFacts(
                project="shop",
                milestone="M5",
                branch="integration/currents",
                opened_pull_request=90,
                pull_request=PullRequestFacts(
                    number=90, state="open", checks=(), review=None, behind=False, head="abc123", base="main"
                ),
            ),
        )
        snapshot = Snapshot(now=datetime(2026, 10, 18, 12, 0, tzinfo=UTC), milestones=milestones)

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            document["milestones"],
            [
                {
                    "project": "shop",
                    "milestone": "M4",
                    "branch": "integration/tides",
                    "merged_waves": [{"wave": "shop_w1", "pr": 77}],
                    "open_waves": ["shop_w3"],
                    "todo": ["S5"],
                    "opened_pull_request": None,
                    "pull_request": None,
                },
                {
                    "project": "shop",
                    "milestone": "M5",
                    "branch": "integration/currents",
                    "merged_waves": [],
                    "open_waves": [],
                    "todo": [],
                    "opened_pull_request": 90,
                    "pull_request": {
                        "number": 90,
                        "state": "open",
                        "checks": [],
                        "review": None,
                        "behind": False,
                        "head": "abc123",
                        "base": "main",
                    },
                },
            ],
        )

    def test_should_carry_the_studies_and_their_live_runs_in_its_document(self):
        # Arrange
        weekly = StudyFacts(
            name="weekly",
            slot="report",
            every="daily@09:00",
            status="active",
            last_started=datetime(2026, 10, 5, 7, 0, 2, tzinfo=UTC),
            parked=False,
        )
        live = LiveStudyRun(study="weekly", run="20261006T110000Z-a1b2c3")
        snapshot = Snapshot(now=datetime(2026, 10, 6, 12, 0, tzinfo=UTC), studies=(weekly,), live_study_runs=(live,))

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            document["studies"],
            [
                {
                    "study": "weekly",
                    "slot": "report",
                    "every": "daily@09:00",
                    "status": "active",
                    "last_started": "2026-10-05T07:00:02Z",
                    "parked": False,
                }
            ],
        )
        self.assertEqual(document["live_study_runs"], [{"study": "weekly", "run": "20261006T110000Z-a1b2c3"}])

    def test_should_carry_the_pause_of_a_wave_and_the_rate_limit_of_its_task_in_its_document(self):
        # Arrange
        task = TaskFacts(name="@TASK.B19", rate_limit=RateLimit(reset=ResetHour(hour="7pm", timezone="Europe/Paris")))
        wave = WaveFacts(
            project="brigade",
            wave="w1",
            branch="main",
            tasks=(task,),
            pause=WavePause(reason="quota", resume_at=datetime(2026, 10, 18, 17, 0, tzinfo=UTC)),
        )
        snapshot = Snapshot(now=datetime(2026, 10, 18, 12, 0, tzinfo=UTC), waves=(wave,))

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            document["waves"],
            [
                {
                    "project": "brigade",
                    "wave": "w1",
                    "branch": "main",
                    "tasks": [
                        {
                            "task": "@TASK.B19",
                            "after": [],
                            "blocked_by": [],
                            "pull_request": None,
                            "worktree": None,
                            "rate_limit": {"reset": {"hour": "7pm", "timezone": "Europe/Paris"}},
                            "stopped_run": None,
                            "opened_pull_request": None,
                            "preflighted_head": None,
                            "verdict": None,
                            "reviewed_head": None,
                            "preflight_failures": [],
                            "repair_rounds": 0,
                            "holds_uncommitted_changes": False,
                            "last_run": None,
                            "blocked_run": None,
                            "milestone": None,
                        }
                    ],
                    "states": {},
                    "implemented": [],
                    "pause": {"reason": "quota", "resume_at": "2026-10-18T17:00:00Z"},
                    "forge_account_unavailable": False,
                    "branch_missing": False,
                    "reported": False,
                    "integration_pull_request": None,
                    "opened_integration_pull_request": None,
                    "milestone_branch": None,
                    "unresolved_threads": 0,
                    "blocked_rebase": None,
                }
            ],
        )

    def test_should_carry_the_wave_start_policy_and_the_candidates_of_a_project_in_its_document(self):
        # Arrange
        candidates = (
            CandidateWave(milestone="M9", tasks=("B188", "B189")),
            CandidateWave(milestone=None, tasks=("B190",)),
        )
        project = ProjectFacts(name="brigade", slots=4, wave_start="ask", candidates=candidates)
        snapshot = Snapshot(now=datetime(2026, 10, 20, 12, 0, tzinfo=UTC), projects=(project,))

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            document["projects"],
            [
                {
                    "project": "brigade",
                    "slots": 4,
                    "live_runs": [],
                    "wave_start": "ask",
                    "candidates": [
                        {"milestone": "M9", "tasks": ["B188", "B189"]},
                        {"milestone": None, "tasks": ["B190"]},
                    ],
                    "merge": "rebase",
                    "review": "verdict",
                    "auto_merge": "integration",
                    "verify_rounds": 2,
                    "awaits_check_runs": True,
                    "on_github": False,
                }
            ],
        )


class ProjectFactsTest(unittest.TestCase):
    def test_should_carry_the_forge_facts_of_a_project_in_its_document(self):
        # Arrange
        project = ProjectFacts(name="brigade", slots=4, awaits_check_runs=False, on_github=True)

        # Act
        document = project.to_document()

        # Assert
        self.assertEqual(document["awaits_check_runs"], False)
        self.assertEqual(document["on_github"], True)


class WaveFactsTest(unittest.TestCase):
    def test_should_carry_the_integration_pull_request_the_wave_opened_in_its_document(self):
        # Arrange
        wave = WaveFacts(project="brigade", wave="w1", branch="wave/w1", opened_integration_pull_request=184)

        # Act
        document = wave.to_document()

        # Assert
        self.assertEqual(document["opened_integration_pull_request"], 184)

    def test_should_carry_the_rebase_run_its_branch_waits_on_a_ruling_from_and_the_question_in_its_document(self):
        # Arrange
        wave = WaveFacts(
            project="brigade",
            wave="brigade_w9",
            branch="integration/brigade_w9",
            blocked_rebase=BlockedRun(run="20261030T080000Z-4eba5e", question="Keep the guard or drop it?"),
        )

        # Act
        document = wave.to_document()

        # Assert
        self.assertEqual(
            document["blocked_rebase"], {"run": "20261030T080000Z-4eba5e", "question": "Keep the guard or drop it?"}
        )


class TaskFactsTest(unittest.TestCase):
    def test_should_carry_the_last_verdict_and_the_head_its_verification_ended_on_in_its_document(self):
        # Arrange
        task = TaskFacts(name="B16", verdict=RecordedVerdict(head="4f2a9c1", verdict="pass"), reviewed_head="4f2a9c1")

        # Act
        document = task.to_document()

        # Assert
        self.assertEqual(document["verdict"], {"head": "4f2a9c1", "verdict": "pass"})
        self.assertEqual(document["reviewed_head"], "4f2a9c1")

    def test_should_carry_the_failures_of_its_last_preflight_and_its_repair_rounds_in_its_document(self):
        # Arrange
        task = TaskFacts(
            name="B18",
            preflight_failures=(PreflightFailure(name="checks", findings=("tests: failure",)),),
            repair_rounds=1,
        )

        # Act
        document = task.to_document()

        # Assert
        self.assertEqual(document["preflight_failures"], [{"name": "checks", "findings": ["tests: failure"]}])
        self.assertEqual(document["repair_rounds"], 1)

    def test_should_carry_the_run_its_task_waits_on_a_ruling_from_and_the_question_in_its_document(self):
        for case, blocked_run, expected in [
            ("no run blocked", None, None),
            (
                "a run blocked",
                BlockedRun(run="20261026T091000Z-b10c4d", question="Keep the guard or drop it?"),
                {"run": "20261026T091000Z-b10c4d", "question": "Keep the guard or drop it?"},
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                task = TaskFacts(name="B25", blocked_run=blocked_run)

                # Act
                document = task.to_document()

                # Assert
                self.assertEqual(document["blocked_run"], expected)

    def test_should_carry_the_last_run_naming_it_in_its_document(self):
        # Arrange
        task = TaskFacts(name="B19", last_run="20261022T232947Z-1858d2")

        # Act
        document = task.to_document()

        # Assert
        self.assertEqual(document["last_run"], "20261022T232947Z-1858d2")

    def test_should_carry_the_milestone_of_the_task_in_its_document(self):
        # Arrange
        task = TaskFacts(name="B19", milestone="M4")

        # Act
        document = task.to_document()

        # Assert
        self.assertEqual(document["milestone"], "M4")
