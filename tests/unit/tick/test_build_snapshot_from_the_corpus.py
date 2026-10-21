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
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_started import WaveStarted
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.system.read_configuration import Configuration
from brigade.tick.build_snapshot import (
    ProjectFacts,
    RateLimit,
    RecordedVerdict,
    Snapshot,
    StudyFacts,
    TaskFacts,
    WaveFacts,
    build_snapshot,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.ledger.create_run_finished import create_run_finished
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

WAVE_SHA = "abc123"
MAIN_SHA = "def456"
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-build-slot"}
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


def describe_task(status: str, *after: str) -> list[dict]:
    return [{"name": "STATUS", "atoms": [status]}, *({"name": "AFTER", "atoms": [f"@TASK.{task}"]} for task in after)]


def answer_tree(ref: str, sha: str) -> dict:
    argv = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")
    return {argv: ProcessAnswer(stdout=f"{sha}\n")}


def answer_unreadable_tree(ref: str) -> dict:
    argv = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")
    return {argv: ProcessAnswer(exit_code=128, stderr="fatal: bad revision")}


def answer_no_incoming_refs(root: Path, *tasks: str) -> dict:
    return {
        ("awawa", "refs", f"@TASK.{task}", "--json", str(root)): ProcessAnswer(stdout=json.dumps({"incoming": []}))
        for task in tasks
    }


def _read_forge_environment(slot: str) -> dict:
    return FORGE_ENVIRONMENT


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
        self.wave_tree = self.paths.cache_root / "refs" / "shop" / WAVE_SHA
        self.wave_tree.mkdir(parents=True)
        self.main_tree = self.paths.cache_root / "refs" / "shop" / MAIN_SHA
        self.main_tree.mkdir(parents=True)
        self.reader = PullRequestReader()
        self.shop_forge = "none"
        self.remote_answers = {}

    def write_operational_corpus(self) -> None:
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def record(self, minutes_ago: int, event) -> None:
        append_event(self.paths, FIXED_NOW - timedelta(minutes=minutes_ago), event)

    def create_runner(self) -> RecordingProcessRunner:
        config_root = self.paths.config_root
        return RecordingProcessRunner(
            {
                **create_registry_answers(
                    config_root,
                    {
                        "shop": {
                            "PATH": str(self.repository),
                            "SLOTS": "2",
                            "CHECK_RUNS": "none",
                            "MAIN": "main",
                            "FORGE": self.shop_forge,
                        },
                        "depot": {"PATH": str(self.root / "depot"), "STATUS": "paused"},
                        "attic": {"PATH": str(self.root / "attic"), "MAIN": "trunk"},
                    },
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
                ("git", "rev-parse", "--verify", "--quiet", "refs/heads/integration/w4"): ProcessAnswer(exit_code=1),
                **answer_tree("integration/w1", WAVE_SHA),
                **answer_unreadable_tree("integration/w5"),
                **answer_entities(
                    self.wave_tree,
                    "TASK",
                    {"B1": describe_task("todo", "B0"), "B2": [], "B3": [], "B4": []},
                ),
                **answer_no_incoming_refs(self.wave_tree, "B1", "B2", "B3", "B4"),
                **answer_entities(self.wave_tree, "TASK", {"B0": []}, "STATUS==implemented"),
                **answer_tree("main", MAIN_SHA),
                **answer_entities(
                    self.main_tree,
                    "TASK",
                    {
                        "B0": describe_task("implemented"),
                        "B1": describe_task("todo", "B0"),
                        "B5": describe_task("todo", "B0"),
                        "B6": describe_task("draft"),
                    },
                ),
                **answer_no_incoming_refs(self.main_tree, "B5"),
                **answer_unreadable_tree("trunk"),
                **self.remote_answers,
            }
        )

    def build(self) -> tuple[Snapshot, str]:
        runtime = create_test_runtime(self.paths, run_process=self.create_runner())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            snapshot = build_snapshot(runtime, Configuration(), self.reader, _read_forge_environment)
        return snapshot, stderr.getvalue()


class BuildSnapshotWithoutCorpusTest(BuildSnapshotTestCase):
    def test_should_answer_an_empty_snapshot_before_brigade_init(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot, Snapshot(now=FIXED_NOW))


class BuildSnapshotOfTheOpenWavesTest(BuildSnapshotTestCase):
    def setUp(self):
        super().setUp()
        self.write_operational_corpus()
        self.record(60, WaveStarted(wave="w1", project="shop", branch="integration/w1", tasks=("B1", "B2", "B3", "B4")))
        self.record(60, WaveStarted(wave="w4", project="shop", branch="integration/w4", tasks=("B7",)))
        self.record(60, WaveStarted(wave="w5", project="shop", branch="integration/w5", tasks=("B8",)))
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

    def test_should_describe_the_wave_from_its_branch_and_the_ledger(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        wave = snapshot.waves[0]
        self.assertEqual(
            (wave.wave, wave.implemented, wave.forge_account_unavailable, wave.reported),
            ("w1", ("B0",), True, False),
        )

    def test_should_follow_no_wave_closed_or_cancelled(self):
        # Arrange
        self.record(40, WaveStarted(wave="w2", project="shop", branch="integration/w2", tasks=("B9",)))
        self.record(30, WaveClosed(wave="w2", pr=31))
        self.record(40, WaveStarted(wave="w3", project="shop", branch="integration/w3", tasks=("B10",)))
        self.record(30, WaveCancelled(wave="w3", reason="user"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(len(snapshot.waves), 2)

    def test_should_carry_the_integration_pull_request_of_a_reported_wave(self):
        # Arrange
        self.record(10, WaveReported(wave="w1", run=None))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot.waves[0].integration_pull_request, PULL_REQUEST)

    def test_should_mark_a_wave_whose_branch_is_gone(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[1],
            WaveFacts(project="shop", wave="w4", branch="integration/w4", branch_missing=True),
        )

    def test_should_mark_a_wave_whose_branch_the_remote_lacks_on_the_github_forge(self):
        # Arrange
        self.shop_forge = "github"
        argv = ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", "refs/heads/integration/w1")
        self.remote_answers = {argv: ProcessAnswer(exit_code=2)}

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[0],
            WaveFacts(project="shop", wave="w1", branch="integration/w1", branch_missing=True),
        )

    def test_should_describe_each_readable_project_with_the_tasks_a_wave_may_take(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.projects,
            (
                ProjectFacts(name="depot", slots=4),
                ProjectFacts(name="shop", slots=2, awaits_check_runs=False, candidates=("B5",)),
            ),
        )

    def test_should_carry_the_rate_limits_in_force_and_the_studies(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            (len(snapshot.rate_limits), snapshot.studies),
            (
                2,
                (
                    StudyFacts(
                        name="flakes", slot="explore", every=None, status="active", last_started=None, parked=False
                    ),
                ),
            ),
        )

    def test_should_skip_a_wave_or_a_project_whose_tree_cannot_be_read(self):
        # Act
        _, stderr = self.build()

        # Assert
        self.assertEqual(
            stderr.splitlines(),
            [
                (
                    "brigade tick: the wave w5 skipped: git rev-parse --verify --quiet --end-of-options"
                    " integration/w5^{commit} exited 128: fatal: bad revision"
                ),
                (
                    "brigade tick: the project attic skipped: git rev-parse --verify --quiet --end-of-options"
                    " trunk^{commit} exited 128: fatal: bad revision"
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
        self.record(60, WaveStarted(wave="w1", project="shop", branch="integration/w1", tasks=("B1", "B2", "B3", "B4")))
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
