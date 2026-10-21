import contextlib
import dataclasses
import io
import json
import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_state import TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.wave_started import WaveStarted
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.system.read_configuration import Configuration
from brigade.tick.build_snapshot import (
    PlannedRequest,
    ProjectFacts,
    RateLimit,
    RecordedVerdict,
    Snapshot,
    StudyFacts,
    TaskFacts,
    build_snapshot,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.ledger.create_run_finished import create_run_finished
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

WAVE_SHA = "abc123"
PULL_REQUEST = PullRequestFacts(number=7, state="open", checks=(), review=None, behind=False, head="4f2a9c1")


def answer_entities(root: Path, entity_type: str, entities: dict[str, list[dict]], *conditions: str) -> dict:
    filters = tuple(argument for condition in conditions for argument in ("--where", condition))
    status = {"entities": [{"type": entity_type, "name": name} for name in entities]}
    return {
        ("awawa", "status", entity_type, *filters, "--json", str(root)): ProcessAnswer(stdout=json.dumps(status)),
        **{
            ("awawa", "show", f"@{entity_type}.{name}", "--json", str(root)): ProcessAnswer(
                stdout=json.dumps({"fields": fields})
            )
            for name, fields in entities.items()
        },
    }


def describe_request(project: str, status: str, branch: str) -> list[dict]:
    return [
        {"name": "PROJECT", "atoms": [f"@PROJECT.{project}"]},
        {"name": "STATUS", "atoms": [status]},
        {"name": "MILESTONE", "atoms": ["M1"]},
        {"name": "BRANCH", "atoms": [json.dumps(branch)]},
    ]


class PullRequestReader:
    def __init__(self):
        self.branches = []

    def __call__(self, repository: str, branch: str) -> PullRequestFacts:
        self.branches.append(branch)
        return PULL_REQUEST


class BuildSnapshotTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.repository = self.root / "shop"
        (self.repository / ".brigade" / "worktrees" / "B1").mkdir(parents=True)
        self.tree = self.paths.cache_root / "refs" / "shop" / WAVE_SHA
        self.tree.mkdir(parents=True)
        self.reader = PullRequestReader()

    def write_operational_corpus(self) -> None:
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def record(self, minutes_ago: int, event) -> None:
        append_event(self.paths, FIXED_NOW - timedelta(minutes=minutes_ago), event)

    def create_runner(self) -> RecordingProcessRunner:
        config_root = self.paths.config_root
        return RecordingProcessRunner(
            {
                **answer_entities(
                    config_root,
                    "REQUEST",
                    {
                        "R1": describe_request("shop", "running", "integration/w1"),
                        "R2": describe_request("shop", "planned", "integration/w2"),
                        "R3": describe_request("shop", "running", "integration/w9"),
                        "R4": describe_request("shop", "running", "integration/w4"),
                    },
                ),
                **create_registry_answers(
                    config_root, {"shop": {"PATH": str(self.repository), "SLOTS": "2", "CHECK_RUNS": "none"}}
                ),
                **answer_entities(config_root, "POLICY", {}),
                **answer_entities(
                    config_root,
                    "STUDY",
                    {
                        "flakes": [
                            {"name": "SLOT", "atoms": ["explore"]},
                            {"name": "OUTPUT", "atoms": ['"flakes.md"']},
                            {"name": "ANSWER", "atoms": ["markdown"]},
                            {"name": "STATUS", "atoms": ["active"]},
                        ]
                    },
                ),
                (
                    "git",
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    "--end-of-options",
                    "integration/w1^{commit}",
                ): ProcessAnswer(stdout=f"{WAVE_SHA}\n"),
                (
                    "git",
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    "--end-of-options",
                    "integration/w4^{commit}",
                ): ProcessAnswer(exit_code=128, stderr="fatal: bad revision"),
                **answer_entities(
                    self.tree,
                    "TASK",
                    {"B1": [{"name": "AFTER", "atoms": ["@TASK.B0"]}], "B2": [], "B3": [], "B4": []},
                    "MILESTONE==@MILESTONE.M1",
                ),
                **{
                    ("awawa", "refs", f"@TASK.{task}", "--json", str(self.tree)): ProcessAnswer(
                        stdout=json.dumps({"incoming": []})
                    )
                    for task in ("B1", "B2", "B3", "B4")
                },
                **answer_entities(self.tree, "TASK", {"B0": []}, "STATUS==implemented"),
            }
        )

    def build(self) -> tuple[Snapshot, str]:
        runtime = create_test_runtime(self.paths, run_process=self.create_runner())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            snapshot = build_snapshot(runtime, Configuration(), self.reader)
        return snapshot, stderr.getvalue()


class BuildSnapshotWithoutCorpusTest(BuildSnapshotTestCase):
    def test_should_answer_an_empty_snapshot_before_brigade_init(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot, Snapshot(now=FIXED_NOW))


class BuildSnapshotOfARunningWaveTest(BuildSnapshotTestCase):
    def setUp(self):
        super().setUp()
        self.write_operational_corpus()
        self.record(60, WaveStarted(wave="w1", project="shop", branch="integration/w1", tasks=("B1",)))
        self.record(60, WaveStarted(wave="w4", project="shop", branch="integration/w4", tasks=("B1",)))
        self.record(50, TaskState(wave="w1", task="B1", state="running"))
        self.record(50, TaskState(wave="w1", task="B2", state="paused:quota"))
        self.record(50, TaskState(wave="w1", task="B3", state="merged"))
        self.record(50, TaskState(wave="w1", task="B4", state="running"))
        self.record(2, create_run_finished("r1", wave="w1", task="B1", outcome="failed", error_class="rate_limit"))
        self.record(1, create_run_finished("r2", wave="w1", task="B2", outcome="failed", error_class="rate_limit"))
        self.record(20, ForgeAccountUnavailable(login="octo-builder", key="build"))

    def test_should_follow_each_task_of_the_wave_by_its_state(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[0].tasks,
            (
                TaskFacts(
                    name="B1",
                    after=("B0",),
                    pull_request=PULL_REQUEST,
                    worktree=str(self.repository / ".brigade" / "worktrees" / "B1"),
                    rate_limit=RateLimit(reset=None),
                ),
                TaskFacts(name="B2", pull_request=PULL_REQUEST, stopped_run="r2"),
                TaskFacts(name="B3"),
                TaskFacts(name="B4", pull_request=PULL_REQUEST),
            ),
        )

    def test_should_describe_the_wave_its_project_and_the_requests_planned(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        wave = snapshot.waves[0]
        self.assertEqual(
            (
                len(snapshot.waves),
                wave.wave,
                wave.implemented,
                wave.forge_account_unavailable,
                snapshot.projects,
                snapshot.planned,
                len(snapshot.rate_limits),
                snapshot.to_document()["projects"],
                snapshot.to_document()["planned"],
                snapshot.studies,
            ),
            (
                1,
                "w1",
                ("B0",),
                True,
                (ProjectFacts(name="shop", slots=2, awaits_check_runs=False),),
                (PlannedRequest(request="R2", project="shop", plan_review="auto"),),
                2,
                [{"project": "shop", "slots": 2, "live_runs": []}],
                [{"request": "R2", "project": "shop", "plan_review": "auto"}],
                (
                    StudyFacts(
                        name="flakes", slot="explore", every=None, status="active", last_started=None, parked=False
                    ),
                ),
            ),
        )

    def test_should_skip_a_request_without_wave_or_whose_tree_cannot_be_read(self):
        # Act
        _, stderr = self.build()

        # Assert
        self.assertEqual(
            stderr.splitlines(),
            [
                (
                    "brigade tick: @REQUEST.R3 skipped: no wave.started of @PROJECT.shop names integration/w9,"
                    " the BRANCH of @REQUEST.R3"
                ),
                (
                    "brigade tick: @REQUEST.R4 skipped: git rev-parse --verify --quiet --end-of-options"
                    " integration/w4^{commit} exited 128: fatal: bad revision"
                ),
            ],
        )


def create_review_run_finished(run: str, task: str, error_class: str | None = None) -> RunFinished:
    return dataclasses.replace(
        create_run_finished(run, procedure="verify-pr", wave="w1", task=task, error_class=error_class), slot="review"
    )


def create_verdict(task: str, head: str, verdict: str) -> TaskVerdict:
    return TaskVerdict(project="shop", wave="w1", task=task, pr=7, head=head, verdict=verdict, findings=(), login=None)


def create_preflight(task: str) -> TaskPreflighted:
    return TaskPreflighted(project="shop", wave="w1", task=task, pr=7, head="4f2a9c1", checks=())


class BuildSnapshotOfTasksInVerifyingTest(BuildSnapshotTestCase):
    def setUp(self):
        super().setUp()
        self.write_operational_corpus()
        self.record(60, WaveStarted(wave="w1", project="shop", branch="integration/w1", tasks=("B1",)))
        self.record(60, WaveStarted(wave="w4", project="shop", branch="integration/w4", tasks=("B1",)))
        self.record(50, TaskState(wave="w1", task="B1", state="verifying"))
        self.record(50, TaskState(wave="w1", task="B2", state="verifying"))
        self.record(50, TaskState(wave="w1", task="B4", state="verifying"))
        self.record(45, create_verdict("B1", "0e1d2c3", "pass"))
        self.record(45, create_preflight("B2"))
        self.record(42, create_review_run_finished("r0", "B2"))
        self.record(40, create_preflight("B1"))
        self.record(40, create_preflight("B2"))
        self.record(40, create_preflight("B4"))
        self.record(31, create_verdict("B1", "4f2a9c1", "changes"))
        self.record(30, create_review_run_finished("r1", "B1"))
        self.record(30, create_review_run_finished("r2", "B2", error_class="rate_limit"))
        self.record(30, create_run_finished("r4", wave="w1", task="B4"))
        self.record(
            29,
            dataclasses.replace(create_run_finished("r5", procedure="verify-pr", wave="w4", task="B4"), slot="review"),
        )

    def test_should_carry_the_last_verdict_of_each_task_and_the_head_its_verification_ended_on(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[0].tasks,
            (
                TaskFacts(
                    name="B1",
                    after=("B0",),
                    pull_request=PULL_REQUEST,
                    worktree=str(self.repository / ".brigade" / "worktrees" / "B1"),
                    preflighted_head="4f2a9c1",
                    verdict=RecordedVerdict(head="4f2a9c1", verdict="changes"),
                    reviewed_head="4f2a9c1",
                ),
                TaskFacts(name="B2", pull_request=PULL_REQUEST, preflighted_head="4f2a9c1"),
                TaskFacts(name="B3"),
                TaskFacts(name="B4", pull_request=PULL_REQUEST, preflighted_head="4f2a9c1"),
            ),
        )
