import contextlib
import dataclasses
import io
import json
import os
import shutil
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from brigade.errors import CommandFailed
from brigade.ledger.append_event import append_event
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_state import TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.runs.record_run_pid import record_run_pid
from brigade.system.parse_configuration import Configuration
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.tick.build_snapshot import (
    BlockedRun,
    ForgeReaders,
    LiveRun,
    PreflightFailure,
    ProjectFacts,
    RateLimit,
    RecordedVerdict,
    Snapshot,
    StudyFacts,
    TaskFacts,
    UncutMilestone,
    WaveFacts,
    build_snapshot,
)
from brigade.waves.list_candidate_waves import CandidateWave
from tests.unit.commands.run_directories import FIRST_RUN, SECOND_RUN, create_run_record, create_run_result, write_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.ledger.create_run_finished import create_run_finished
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

WAVE_SHA = "abc123"
MAIN_SHA = "def456"
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-build-slot"}
PULL_REQUEST = PullRequestFacts(
    number=7,
    state="open",
    checks=(),
    review=None,
    behind=False,
    head="4f2a9c1",
    base="integration/w1",
    updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
)
from brigade.system.run_process import ProcessRequest
from tests.unit.select_requests_opening_on import select_requests_opening_on


class AwawaAnswerWriterDouble:
    def answer_entities(self, root: Path, entity_type: str, entities: dict[str, list[dict]], *conditions: str) -> dict:
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

    def describe_task(self, status: str, *after: str) -> list[dict]:
        return [
            {"name": "STATUS", "atoms": [status]},
            *({"name": "AFTER", "atoms": [f"@TASK.{task}"]} for task in after),
        ]

    def answer_no_incoming_refs(self, root: Path, *tasks: str) -> dict:
        return {
            ("awawa", "refs", f"@TASK.{task}", "--json", str(root)): ProcessAnswer(stdout=json.dumps({"incoming": []}))
            for task in tasks
        }


AWAWA_ANSWERS = AwawaAnswerWriterDouble()


def answer_tree(ref: str, sha: str) -> dict:
    argv = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")
    return {argv: ProcessAnswer(stdout=f"{sha}\n")}


def answer_main_of_the_forge(sha: str) -> dict:
    return {("git", "fetch", "--quiet", "origin", "main"): ProcessAnswer(), **answer_tree("origin/main", sha)}


def answer_unreadable_tree(ref: str) -> dict:
    argv = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}")
    return {argv: ProcessAnswer(exit_code=128, stderr="fatal: bad revision")}


def _read_forge_environment(slot: str) -> dict:
    return FORGE_ENVIRONMENT


def _count_no_thread(repository: str, number: int) -> int:
    return 0


class PullRequestReaderDouble:
    def __init__(self):
        self.branches = []

    def __call__(self, repository: str, branch: str) -> PullRequestFacts:
        self.branches.append(branch)
        return PULL_REQUEST


class PullRequestReaderFailingOnOneWaveDouble(PullRequestReaderDouble):
    def __call__(self, repository: str, branch: str) -> PullRequestFacts:
        if branch == "task/w1/B1":
            raise CommandFailed(("gh", "pr", "list", "--head", branch), 1, "HTTP 502: Bad Gateway")
        return super().__call__(repository, branch)


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
        self.reader = PullRequestReaderDouble()
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
                            "MERGE": "squash",
                        },
                        "depot": {"PATH": str(self.root / "depot"), "STATUS": "paused"},
                        "attic": {"PATH": str(self.root / "attic"), "MAIN": "trunk"},
                    },
                ),
                **AWAWA_ANSWERS.answer_entities(
                    config_root,
                    "POLICY",
                    {
                        "shop_policy": [
                            {"name": "PROJECT", "atoms": ["@PROJECT.shop"]},
                            {"name": "REVIEW", "atoms": ["approval"]},
                            {"name": "AUTO_MERGE", "atoms": ["none"]},
                            {"name": "VERIFY_ROUNDS", "atoms": ["3"]},
                        ]
                    },
                ),
                **AWAWA_ANSWERS.answer_entities(
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
                **AWAWA_ANSWERS.answer_entities(
                    self.wave_tree,
                    "TASK",
                    {
                        "B1": AWAWA_ANSWERS.describe_task("todo", "B0"),
                        "B2": [],
                        "B3": [{"name": "MILESTONE", "atoms": ["@MILESTONE.M4"]}],
                        "B4": [],
                    },
                ),
                **AWAWA_ANSWERS.answer_no_incoming_refs(self.wave_tree, "B1", "B2", "B3", "B4"),
                **AWAWA_ANSWERS.answer_entities(self.wave_tree, "TASK", {"B0": []}, "STATUS==implemented"),
                **answer_tree("main", MAIN_SHA),
                **AWAWA_ANSWERS.answer_entities(
                    self.main_tree,
                    "TASK",
                    {
                        "B0": AWAWA_ANSWERS.describe_task("implemented"),
                        "B1": AWAWA_ANSWERS.describe_task("todo", "B0"),
                        "B5": AWAWA_ANSWERS.describe_task("todo", "B0"),
                        "B6": AWAWA_ANSWERS.describe_task("draft"),
                    },
                ),
                **AWAWA_ANSWERS.answer_no_incoming_refs(self.main_tree, "B5"),
                **AWAWA_ANSWERS.answer_entities(self.main_tree, "MILESTONE", {}, "STATUS==active"),
                **answer_unreadable_tree("trunk"),
                **self.remote_answers,
            }
        )

    def build(self) -> tuple[Snapshot, str]:
        self.runner = self.create_runner()
        runtime = create_test_runtime(self.paths, run_process=self.runner)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            snapshot = build_snapshot(
                runtime, Configuration(), ForgeReaders(self.reader, _read_forge_environment, _count_no_thread)
            )
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
                TaskFacts(name="B3", milestone="M4"),
                TaskFacts(name="B4", pull_request=PULL_REQUEST),
            ),
        )

    def test_should_name_the_last_run_naming_each_task_of_the_wave(self):
        # Arrange
        write_run(self.paths.state_root, create_run_record("20261013T080000Z-a00001", "w1", "B4"), None)
        write_run(self.paths.state_root, create_run_record("20261013T090000Z-a00002", "w1", "B4"), None)
        write_run(self.paths.state_root, create_run_record("20261013T100000Z-a00003", "w1", "B1"), None)
        write_run(self.paths.state_root, create_run_record("20261013T110000Z-a00004", "w4", "B4"), None)

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
                    last_run="20261013T100000Z-a00003",
                ),
                TaskFacts(name="B2", pull_request=PULL_REQUEST, stopped_run="r2"),
                TaskFacts(name="B3", milestone="M4"),
                TaskFacts(name="B4", pull_request=PULL_REQUEST, last_run="20261013T090000Z-a00002"),
            ),
        )

    def test_should_tell_that_the_worktree_of_a_task_holds_uncommitted_changes(self):
        # Arrange
        self.remote_answers = {
            ("git", "status", "--porcelain", "--untracked-files=no"): ProcessAnswer(stdout=" M brigade/cli.py\n")
        }

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
                    holds_uncommitted_changes=True,
                ),
                TaskFacts(name="B2", pull_request=PULL_REQUEST, stopped_run="r2"),
                TaskFacts(name="B3", milestone="M4"),
                TaskFacts(name="B4", pull_request=PULL_REQUEST),
            ),
        )

    def test_should_describe_the_wave_from_its_branch_and_the_ledger(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        wave = snapshot.waves[0]
        self.assertEqual(wave.wave, "w1")
        self.assertEqual(wave.implemented, ("B0",))
        self.assertEqual(wave.forge_account_unavailable, True)
        self.assertEqual(wave.reported, False)

    def test_should_follow_no_wave_closed_or_cancelled(self):
        # Arrange
        self.record(40, WaveStarted(wave="w2", project="shop", branch="integration/w2", tasks=("B9",)))
        self.record(30, WaveClosed(wave="w2", pr=31))
        self.record(40, WaveStarted(wave="w3", project="shop", branch="integration/w3", tasks=("B10",)))
        self.record(30, WaveCancelled(wave="w3", reason="user"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves,
            (
                WaveFacts(
                    project="shop",
                    wave="w1",
                    branch="integration/w1",
                    tasks=(
                        TaskFacts(
                            name="B1",
                            after=("B0",),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=f"{self.root}/shop/.brigade/worktrees/B1",
                            rate_limit=RateLimit(reset=None),
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B2",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run="r2",
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B3",
                            milestone="M4",
                            after=(),
                            blocked_by=(),
                            pull_request=None,
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B4",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                    ),
                    states={"B1": "running", "B2": "paused:quota", "B3": "merged", "B4": "running"},
                    implemented=("B0",),
                    pause=None,
                    forge_account_unavailable=True,
                    branch_missing=False,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
                WaveFacts(
                    project="shop",
                    wave="w4",
                    branch="integration/w4",
                    tasks=(),
                    states={},
                    implemented=(),
                    pause=None,
                    forge_account_unavailable=False,
                    branch_missing=True,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
            ),
        )

    def test_should_carry_the_integration_pull_request_of_a_reported_wave(self):
        # Arrange
        self.record(10, WaveReported(wave="w1", run=None))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves,
            (
                WaveFacts(
                    project="shop",
                    wave="w1",
                    branch="integration/w1",
                    tasks=(
                        TaskFacts(
                            name="B1",
                            after=("B0",),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=f"{self.root}/shop/.brigade/worktrees/B1",
                            rate_limit=RateLimit(reset=None),
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B2",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run="r2",
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B3",
                            milestone="M4",
                            after=(),
                            blocked_by=(),
                            pull_request=None,
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B4",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                    ),
                    states={"B1": "running", "B2": "paused:quota", "B3": "merged", "B4": "running"},
                    implemented=("B0",),
                    pause=None,
                    forge_account_unavailable=True,
                    branch_missing=False,
                    reported=True,
                    integration_pull_request=PullRequestFacts(
                        number=7,
                        state="open",
                        checks=(),
                        review=None,
                        behind=False,
                        head="4f2a9c1",
                        base="integration/w1",
                        updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                    ),
                    opened_integration_pull_request=None,
                ),
                WaveFacts(
                    project="shop",
                    wave="w4",
                    branch="integration/w4",
                    tasks=(),
                    states={},
                    implemented=(),
                    pause=None,
                    forge_account_unavailable=False,
                    branch_missing=True,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
            ),
        )

    def test_should_carry_the_integration_pull_request_the_ledger_records_as_opened(self):
        # Arrange
        self.record(10, WavePrOpened(wave="w1", pr=77, login="shop-cli"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves,
            (
                WaveFacts(
                    project="shop",
                    wave="w1",
                    branch="integration/w1",
                    tasks=(
                        TaskFacts(
                            name="B1",
                            after=("B0",),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=f"{self.root}/shop/.brigade/worktrees/B1",
                            rate_limit=RateLimit(reset=None),
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B2",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run="r2",
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B3",
                            milestone="M4",
                            after=(),
                            blocked_by=(),
                            pull_request=None,
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B4",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                    ),
                    states={"B1": "running", "B2": "paused:quota", "B3": "merged", "B4": "running"},
                    implemented=("B0",),
                    pause=None,
                    forge_account_unavailable=True,
                    branch_missing=False,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=77,
                ),
                WaveFacts(
                    project="shop",
                    wave="w4",
                    branch="integration/w4",
                    tasks=(),
                    states={},
                    implemented=(),
                    pause=None,
                    forge_account_unavailable=False,
                    branch_missing=True,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
            ),
        )

    def test_should_describe_a_project_on_the_github_forge(self):
        # Arrange
        self.shop_forge = "github"
        argv = ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", "refs/heads/integration/w1")
        self.remote_answers = {argv: ProcessAnswer(), **answer_main_of_the_forge(MAIN_SHA)}

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.projects[1],
            ProjectFacts(
                name="shop",
                slots=2,
                awaits_check_runs=False,
                candidates=(CandidateWave(milestone=None, tasks=("B5",)),),
                merge="squash",
                review="approval",
                auto_merge="none",
                verify_rounds=3,
                on_github=True,
            ),
        )

    def test_should_fetch_the_main_branch_with_the_environment_of_the_forge_on_github(self):
        # Arrange
        self.shop_forge = "github"
        argv = ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", "refs/heads/integration/w1")
        self.remote_answers = {argv: ProcessAnswer(), **answer_main_of_the_forge(MAIN_SHA)}

        # Act
        self.build()

        # Assert
        fetch_of_main = ProcessRequest(
            argv=("git", "fetch", "--quiet", "origin", "main"),
            cwd=str(self.repository),
            timeout_s=120.0,
            environment=FORGE_ENVIRONMENT,
        )
        self.assertEqual(
            select_requests_opening_on(self.runner.requests, ("git", "fetch")), [fetch_of_main, fetch_of_main]
        )

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
        self.remote_answers = {argv: ProcessAnswer(exit_code=2), **answer_main_of_the_forge(MAIN_SHA)}

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
                ProjectFacts(name="depot", slots=4, merge="rebase", review="verdict", auto_merge="integration"),
                ProjectFacts(
                    name="shop",
                    slots=2,
                    awaits_check_runs=False,
                    candidates=(CandidateWave(milestone=None, tasks=("B5",)),),
                    merge="squash",
                    review="approval",
                    auto_merge="none",
                    verify_rounds=3,
                ),
            ),
        )

    def test_should_carry_the_rate_limits_in_force_and_the_studies(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot.rate_limits, (RateLimit(reset=None), RateLimit(reset=None)))
        self.assertEqual(
            snapshot.studies,
            (
                StudyFacts(name="flakes", slot="explore", every=None, status="active", last_started=None, parked=False),
                StudyFacts(name="triage", slot="triage", every="24h", status="active", last_started=None, parked=False),
            ),
        )

    def test_should_carry_no_rate_limit_whose_reset_has_passed(self):
        # Arrange
        self.record(120, create_run_finished("r9", outcome="failed", error_class="rate_limit"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot.rate_limits, (RateLimit(reset=None), RateLimit(reset=None)))

    def test_should_note_no_rate_limit_on_a_merged_task_whose_last_run_hit_one(self):
        # Arrange
        self.record(3, create_run_finished("r3", wave="w1", task="B3", outcome="failed", error_class="rate_limit"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves,
            (
                WaveFacts(
                    project="shop",
                    wave="w1",
                    branch="integration/w1",
                    tasks=(
                        TaskFacts(
                            name="B1",
                            after=("B0",),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=f"{self.root}/shop/.brigade/worktrees/B1",
                            rate_limit=RateLimit(reset=None),
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B2",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run="r2",
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B3",
                            milestone="M4",
                            after=(),
                            blocked_by=(),
                            pull_request=None,
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B4",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                    ),
                    states={"B1": "running", "B2": "paused:quota", "B3": "merged", "B4": "running"},
                    implemented=("B0",),
                    pause=None,
                    forge_account_unavailable=True,
                    branch_missing=False,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
                WaveFacts(
                    project="shop",
                    wave="w4",
                    branch="integration/w4",
                    tasks=(),
                    states={},
                    implemented=(),
                    pause=None,
                    forge_account_unavailable=False,
                    branch_missing=True,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
            ),
        )

    def test_should_clear_the_unavailable_forge_account_of_a_wave_resumed_from_it(self):
        # Arrange
        self.record(10, WaveResumed(wave="w1", reason="forge_account"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves,
            (
                WaveFacts(
                    project="shop",
                    wave="w1",
                    branch="integration/w1",
                    tasks=(
                        TaskFacts(
                            name="B1",
                            after=("B0",),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=f"{self.root}/shop/.brigade/worktrees/B1",
                            rate_limit=RateLimit(reset=None),
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B2",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run="r2",
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B3",
                            milestone="M4",
                            after=(),
                            blocked_by=(),
                            pull_request=None,
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                        TaskFacts(
                            name="B4",
                            after=(),
                            blocked_by=(),
                            pull_request=PullRequestFacts(
                                number=7,
                                state="open",
                                checks=(),
                                review=None,
                                behind=False,
                                head="4f2a9c1",
                                base="integration/w1",
                                updated_at=datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
                            ),
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                    ),
                    states={"B1": "running", "B2": "paused:quota", "B3": "merged", "B4": "running"},
                    implemented=("B0",),
                    pause=None,
                    forge_account_unavailable=False,
                    branch_missing=False,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
                WaveFacts(
                    project="shop",
                    wave="w4",
                    branch="integration/w4",
                    tasks=(),
                    states={},
                    implemented=(),
                    pause=None,
                    forge_account_unavailable=False,
                    branch_missing=True,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
            ),
        )

    def test_should_read_no_pull_request_of_a_settled_task_whose_worktree_is_gone(self):
        # Act
        self.build()

        # Assert
        self.assertEqual(self.reader.branches, ["task/w1/B1", "task/w1/B2", "task/w1/B4"])

    def test_should_count_the_live_build_runs_of_the_project(self):
        # Arrange
        live_run = {**create_run_record(FIRST_RUN, "w1", "B1"), "project": "shop", "worktree": "/srv/shop/B1"}
        record_run_pid(write_run(self.paths.state_root, live_run, None), os.getpid())

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.projects[1].live_runs,
            (LiveRun(run=FIRST_RUN, slot="build", worktree="/srv/shop/B1", wave="w1", task="B1"),),
        )

    def test_should_leave_out_the_finished_runs_and_the_runs_of_no_project(self):
        # Arrange
        finished_run = {**create_run_record(FIRST_RUN, "w1", "B1"), "project": "shop"}
        write_run(self.paths.state_root, finished_run, create_run_result(FIRST_RUN, "done", "2026-10-19T08:00:00Z"))
        record_run_pid(self.paths.state_root / "runs" / FIRST_RUN, os.getpid())
        run_of_no_project = create_run_record(SECOND_RUN, None, None)
        record_run_pid(write_run(self.paths.state_root, run_of_no_project, None), os.getpid())

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.projects,
            (
                ProjectFacts(
                    name="depot",
                    slots=4,
                    live_runs=(),
                    awaits_check_runs=True,
                    wave_start="auto",
                    candidates=(),
                    merge="rebase",
                    review="verdict",
                    auto_merge="integration",
                    verify_rounds=2,
                    on_github=False,
                ),
                ProjectFacts(
                    name="shop",
                    slots=2,
                    live_runs=(),
                    awaits_check_runs=False,
                    wave_start="auto",
                    candidates=(CandidateWave(milestone=None, tasks=("B5",)),),
                    merge="squash",
                    review="approval",
                    auto_merge="none",
                    verify_rounds=3,
                    on_github=False,
                ),
            ),
        )

    def test_should_skip_a_wave_whose_pull_request_the_forge_refuses_to_read_and_follow_the_others(self):
        # Arrange
        self.reader = PullRequestReaderFailingOnOneWaveDouble()

        # Act
        snapshot, stderr = self.build()

        # Assert
        self.assertEqual(
            stderr.splitlines()[0],
            "brigade tick: the wave w1 skipped: gh pr list --head task/w1/B1 exited 1: HTTP 502: Bad Gateway",
        )
        self.assertEqual(
            snapshot.waves,
            (
                WaveFacts(
                    project="shop",
                    wave="w4",
                    branch="integration/w4",
                    tasks=(),
                    states={},
                    implemented=(),
                    pause=None,
                    forge_account_unavailable=False,
                    branch_missing=True,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
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


class BuildSnapshotOfAWaveStartedAfterTheForgeAccountBecameUnavailableTest(BuildSnapshotTestCase):
    def test_should_mark_the_forge_account_of_the_wave_unavailable(self):
        # Arrange
        self.write_operational_corpus()
        self.record(90, ForgeAccountUnavailable(login="octo-builder", key="build"))
        self.record(60, WaveStarted(wave="w1", project="shop", branch="integration/w1", tasks=("B1",)))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves,
            (
                WaveFacts(
                    project="shop",
                    wave="w1",
                    branch="integration/w1",
                    tasks=(
                        TaskFacts(
                            name="B1",
                            after=("B0",),
                            blocked_by=(),
                            pull_request=None,
                            worktree=None,
                            rate_limit=None,
                            stopped_run=None,
                            opened_pull_request=None,
                            preflighted_head=None,
                            verdict=None,
                            reviewed_head=None,
                            preflight_failures=(),
                            repair_rounds=0,
                            holds_uncommitted_changes=False,
                            last_run=None,
                        ),
                    ),
                    states={},
                    implemented=("B0",),
                    pause=None,
                    forge_account_unavailable=True,
                    branch_missing=False,
                    reported=False,
                    integration_pull_request=None,
                    opened_integration_pull_request=None,
                ),
            ),
        )


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
                TaskFacts(name="B3", milestone="M4"),
                TaskFacts(name="B4", pull_request=PULL_REQUEST, preflighted_head="4f2a9c1"),
            ),
        )

    def test_should_set_aside_the_preflight_and_the_verdict_recorded_before_the_last_requeue_of_the_task(self):
        # Arrange
        self.record(25, dataclasses.replace(create_preflight("B1"), checks=(FAILING_BODY,)))
        self.record(20, TaskState(wave="w1", task="B1", state="pr_open", reason=REQUEUE_REASON))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[0].tasks[0],
            TaskFacts(
                name="B1",
                after=("B0",),
                pull_request=PULL_REQUEST,
                worktree=str(self.repository / ".brigade" / "worktrees" / "B1"),
            ),
        )

    def test_should_set_aside_the_head_reviewed_before_the_last_requeue_of_the_task(self):
        # Arrange
        self.record(20, TaskState(wave="w1", task="B1", state="pr_open", reason=REQUEUE_REASON))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertIsNone(snapshot.waves[0].tasks[0].reviewed_head)

    def test_should_keep_the_preflight_and_the_verdict_of_the_other_tasks_of_the_wave_across_a_requeue(self):
        # Arrange
        self.record(35, create_verdict("B2", "4f2a9c1", "changes"))
        self.record(20, TaskState(wave="w1", task="B1", state="pr_open", reason=REQUEUE_REASON))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[0].tasks[1:],
            (
                TaskFacts(
                    name="B2",
                    pull_request=PULL_REQUEST,
                    preflighted_head="4f2a9c1",
                    verdict=RecordedVerdict(head="4f2a9c1", verdict="changes"),
                ),
                TaskFacts(name="B3", milestone="M4"),
                TaskFacts(name="B4", pull_request=PULL_REQUEST, preflighted_head="4f2a9c1"),
            ),
        )


REQUEUE_REASON = "brigade wave requeue"
FAILING_CHECKS = {"name": "checks", "verdict": "fail", "findings": ["tests: failure"]}
FAILING_BODY = {"name": "body", "verdict": "fail", "findings": ["the body names no task"]}
PASSING_PRIVACY = {"name": "privacy", "verdict": "pass", "findings": []}
MEASURED_SIZE = {"name": "size", "verdict": "info", "findings": ["3 files"]}


class BuildSnapshotOfTasksInRepairTest(BuildSnapshotTestCase):
    def setUp(self):
        super().setUp()
        self.write_operational_corpus()
        self.record(60, WaveStarted(wave="w1", project="shop", branch="integration/w1", tasks=("B1", "B2", "B3", "B4")))
        self.record(60, WaveStarted(wave="w4", project="shop", branch="integration/w4", tasks=("B1",)))
        self.record(50, dataclasses.replace(create_preflight("B1"), checks=(FAILING_BODY,)))
        self.record(49, TaskState(wave="w1", task="B1", state="fixing"))
        self.record(
            40, dataclasses.replace(create_preflight("B1"), checks=(FAILING_CHECKS, PASSING_PRIVACY, MEASURED_SIZE))
        )
        self.record(39, TaskState(wave="w1", task="B1", state="fixing"))
        self.record(38, TaskState(wave="w4", task="B1", state="fixing"))
        self.record(30, TaskState(wave="w1", task="B2", state="changes_requested"))

    def test_should_carry_the_failures_of_the_last_preflight_and_the_repair_rounds_taken(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[0].tasks[:2],
            (
                TaskFacts(
                    name="B1",
                    after=("B0",),
                    pull_request=PULL_REQUEST,
                    worktree=str(self.repository / ".brigade" / "worktrees" / "B1"),
                    preflighted_head="4f2a9c1",
                    preflight_failures=(PreflightFailure(name="checks", findings=("tests: failure",)),),
                    repair_rounds=2,
                ),
                TaskFacts(name="B2", pull_request=PULL_REQUEST),
            ),
        )

    def test_should_count_a_round_for_each_repair_run_and_none_for_a_rebase_run(self):
        for case, second_launch, expected_rounds in [
            ("a check repair after a remediation", ("build", "w1", "B1"), 2),
            ("a rebase run after a remediation", ("rebase", "w1", "B1"), 1),
            ("a rebase run of another task at the same tick", ("rebase", "w1", "B2"), 2),
            ("a rebase run of the task in another wave at the same tick", ("rebase", "w4", "B1"), 2),
        ]:
            with self.subTest(case=case):
                # Arrange
                slot, wave, task = second_launch
                self.setUp()
                write_run(
                    self.paths.state_root,
                    {**create_run_record("20261019T081100Z-a00001", "w1", "B1"), "slot": "remediate"},
                    None,
                )
                write_run(
                    self.paths.state_root,
                    {**create_run_record("20261019T082100Z-a00002", wave, task), "slot": slot},
                    None,
                )

                # Act
                snapshot, _ = self.build()

                # Assert
                self.assertEqual(snapshot.waves[0].tasks[0].repair_rounds, expected_rounds)

    def test_should_count_no_round_recorded_before_the_last_verdict_or_the_last_requeue_of_the_task(self):
        for case, recorded_after_the_rounds, expected_rounds in [
            ("a verdict on the task", create_verdict("B1", "4f2a9c1", "changes"), 0),
            ("a requeue of the task", TaskState(wave="w1", task="B1", state="pr_open", reason=REQUEUE_REASON), 0),
            ("a state the tick records", TaskState(wave="w1", task="B1", state="pr_open"), 2),
            ("a verdict on another task", create_verdict("B2", "4f2a9c1", "changes"), 2),
            (
                "a requeue of the task in another wave",
                TaskState(wave="w4", task="B1", state="pr_open", reason=REQUEUE_REASON),
                2,
            ),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.setUp()
                self.record(35, recorded_after_the_rounds)

                # Act
                snapshot, _ = self.build()

                # Assert
                self.assertEqual(snapshot.waves[0].tasks[0].repair_rounds, expected_rounds)

    def test_should_count_the_rounds_recorded_after_the_last_requeue_of_the_task(self):
        # Arrange
        self.record(35, TaskState(wave="w1", task="B1", state="pr_open", reason=REQUEUE_REASON))
        self.record(20, TaskState(wave="w1", task="B1", state="fixing"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot.waves[0].tasks[0].repair_rounds, 1)

    def test_should_count_no_round_for_a_repair_run_cut_by_a_rate_limit(self):
        for case, error_class, expected_rounds in [
            ("a repair run cut by a rate limit", "rate_limit", 1),
            ("a repair run ended on another failure", "execution", 2),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.setUp()
                write_run(
                    self.paths.state_root,
                    {**create_run_record("20261019T082100Z-a00002", "w1", "B1"), "slot": "remediate"},
                    None,
                )
                self.record(
                    30,
                    create_run_finished(
                        "20261019T082100Z-a00002", wave="w1", task="B1", outcome="failed", error_class=error_class
                    ),
                )

                # Act
                snapshot, _ = self.build()

                # Assert
                self.assertEqual(snapshot.waves[0].tasks[0].repair_rounds, expected_rounds)

    def test_should_count_no_round_for_the_resume_of_a_repair_run_cut_by_a_rate_limit(self):
        # Arrange
        write_run(
            self.paths.state_root,
            {**create_run_record("20261019T082100Z-a00002", "w1", "B1"), "slot": "remediate"},
            None,
        )
        self.record(
            30,
            create_run_finished(
                "20261019T082100Z-a00002", wave="w1", task="B1", outcome="failed", error_class="rate_limit"
            ),
        )
        self.record(29, TaskState(wave="w1", task="B1", state="paused:quota"))
        self.record(20, TaskState(wave="w1", task="B1", state="fixing"))
        self.record(10, create_run_finished("20261019T082100Z-a00002", wave="w1", task="B1", outcome="done"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot.waves[0].tasks[0].repair_rounds, 1)

    def test_should_note_the_rate_limit_of_a_task_in_fixing_whose_repair_run_was_cut(self):
        # Arrange
        self.record(
            5,
            create_run_finished(
                "20261019T085500Z-a00003", wave="w1", task="B1", outcome="failed", error_class="rate_limit"
            ),
        )

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot.waves[0].tasks[0].rate_limit, RateLimit(reset=None))

    def test_should_resume_a_task_paused_on_the_quota_in_the_state_it_held_before_its_pause(self):
        # Arrange
        self.record(
            5,
            create_run_finished(
                "20261019T085500Z-a00003", wave="w1", task="B1", outcome="failed", error_class="rate_limit"
            ),
        )
        self.record(4, TaskState(wave="w1", task="B1", state="paused:quota"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot.waves[0].tasks[0].resumed_state, "fixing")

    def test_should_carry_the_question_of_the_last_run_of_the_task_when_it_ended_blocked(self):
        for case, outcome, message, expected in [
            (
                "a question on one line",
                "blocked",
                "Keep the guard or drop it?\nbrigade-end: blocked",
                BlockedRun(run="20261019T083000Z-b10c4d", question="Keep the guard or drop it?"),
            ),
            (
                "a question over several lines",
                "blocked",
                "The rebase conflicts in plan.py.\n\nKeep the guard or drop it?\nbrigade-end: blocked",
                BlockedRun(
                    run="20261019T083000Z-b10c4d",
                    question="The rebase conflicts in plan.py. Keep the guard or drop it?",
                ),
            ),
            ("no final message", "blocked", None, BlockedRun(run="20261019T083000Z-b10c4d", question="")),
            ("a run delivered", "done", "Pushed.\nbrigade-end: done", None),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.setUp()
                write_run(self.paths.state_root, create_run_record("20261019T081100Z-a00001", "w1", "B1"), None)
                write_run(self.paths.state_root, create_run_record("20261019T083000Z-b10c4d", "w1", "B1"), None)
                self.record(
                    5,
                    dataclasses.replace(
                        create_run_finished("20261019T083000Z-b10c4d", wave="w1", task="B1", outcome=outcome),
                        message=message,
                    ),
                )

                # Act
                snapshot, _ = self.build()

                # Assert
                self.assertEqual(snapshot.waves[0].tasks[0].blocked_run, expected)

    def test_should_note_a_task_rebased_by_its_last_run_when_a_rebase_run_ended_done(self):
        for case, slot, outcome, expected in [
            ("a rebase run delivered", "rebase", "done", True),
            ("a rebase run blocked", "rebase", "blocked", False),
            ("a build run delivered", "build", "done", False),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.setUp()
                write_run(
                    self.paths.state_root,
                    {**create_run_record("20261019T083000Z-4eba5e", "w1", "B1"), "slot": slot},
                    None,
                )
                self.record(5, create_run_finished("20261019T083000Z-4eba5e", wave="w1", task="B1", outcome=outcome))

                # Act
                snapshot, _ = self.build()

                # Assert
                self.assertEqual(snapshot.waves[0].tasks[0].rebased_by_last_run, expected)

    def test_should_note_a_task_whose_last_run_is_a_rebase_run_whatever_its_outcome(self):
        for case, slot, outcome, expected in [
            ("a rebase run delivered", "rebase", "done", True),
            ("a rebase run blocked", "rebase", "blocked", True),
            ("a build run delivered", "build", "done", False),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.setUp()
                write_run(
                    self.paths.state_root,
                    {**create_run_record("20261019T083000Z-4eba5e", "w1", "B1"), "slot": slot},
                    None,
                )
                self.record(5, create_run_finished("20261019T083000Z-4eba5e", wave="w1", task="B1", outcome=outcome))

                # Act
                snapshot, _ = self.build()

                # Assert
                self.assertEqual(snapshot.waves[0].tasks[0].last_run_is_a_rebase, expected)

    def test_should_note_a_task_whose_last_run_is_a_rebase_run_not_finished_yet(self):
        # Arrange
        write_run(
            self.paths.state_root, {**create_run_record("20261019T083000Z-4eba5e", "w1", "B1"), "slot": "rebase"}, None
        )

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertTrue(snapshot.waves[0].tasks[0].last_run_is_a_rebase)

    def test_should_carry_no_blocked_run_while_the_last_run_of_the_task_has_not_finished(self):
        # Arrange
        write_run(self.paths.state_root, create_run_record("20261019T081100Z-a00001", "w1", "B1"), None)
        write_run(self.paths.state_root, create_run_record("20261019T083000Z-b10c4d", "w1", "B1"), None)
        self.record(
            20,
            dataclasses.replace(
                create_run_finished("20261019T081100Z-a00001", wave="w1", task="B1", outcome="blocked"),
                message="Keep the guard or drop it?\nbrigade-end: blocked",
            ),
        )

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertIsNone(snapshot.waves[0].tasks[0].blocked_run)


BLOCKED_REBASE_MESSAGE = "Keep the guard of plan.py or drop it?\nbrigade-end: blocked"
WAVE_BRANCH_RUN = None
PAUSE_ON_THE_BLOCKED_REBASE_RUN = WavePaused(
    wave="w1", reason="run 20261019T083000Z-4eba5e blocked: Keep the guard of plan.py or drop it?", resume_at=None
)


class BuildSnapshotOfARebaseRunOfAWaveBranchTest(BuildSnapshotTestCase):
    def setUp(self):
        super().setUp()
        self.write_operational_corpus()
        self.record(60, WaveStarted(wave="w1", project="shop", branch="integration/w1", tasks=("B1",)))

    def record_rebase_run(self, task: str | None, outcome: str) -> None:
        write_run(
            self.paths.state_root,
            {**create_run_record("20261019T083000Z-4eba5e", "w1", task), "slot": "rebase"},
            None,
        )
        self.record(
            5,
            dataclasses.replace(
                create_run_finished("20261019T083000Z-4eba5e", wave="w1", task=task, outcome=outcome),
                message=BLOCKED_REBASE_MESSAGE,
            ),
        )

    def test_should_carry_the_question_of_the_last_rebase_run_of_the_wave_branch_when_it_ended_blocked(self):
        for case, task, outcome, expected in [
            (
                "a rebase run of the wave branch blocked",
                WAVE_BRANCH_RUN,
                "blocked",
                BlockedRun(run="20261019T083000Z-4eba5e", question="Keep the guard of plan.py or drop it?"),
            ),
            ("a rebase run of the wave branch delivered", WAVE_BRANCH_RUN, "done", None),
            ("a rebase run of a task of the wave blocked", "B1", "blocked", None),
        ]:
            with self.subTest(case=case):
                # Arrange
                self.setUp()
                self.record_rebase_run(task, outcome)

                # Act
                snapshot, _ = self.build()

                # Assert
                self.assertEqual(snapshot.waves[0].blocked_rebase, expected)

    def test_should_carry_no_blocked_rebase_run_once_the_wave_is_paused_on_it(self):
        # Arrange
        self.record_rebase_run(WAVE_BRANCH_RUN, "blocked")
        self.record(4, PAUSE_ON_THE_BLOCKED_REBASE_RUN)

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertIsNone(snapshot.waves[0].blocked_rebase)

    def test_should_carry_no_blocked_rebase_run_once_the_wave_paused_on_it_is_resumed(self):
        # Arrange
        self.record_rebase_run(WAVE_BRANCH_RUN, "blocked")
        self.record(4, PAUSE_ON_THE_BLOCKED_REBASE_RUN)
        self.record(3, WaveResumed(wave="w1", reason="user"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertIsNone(snapshot.waves[0].blocked_rebase)

    def test_should_carry_the_blocked_rebase_run_past_a_quota_pause_of_the_wave_and_its_resume(self):
        # Arrange
        self.record_rebase_run(WAVE_BRANCH_RUN, "blocked")
        self.record(4, WavePaused(wave="w1", reason="quota", resume_at="2026-10-19T10:00:00Z"))
        self.record(3, WaveResumed(wave="w1", reason="quota"))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[0].blocked_rebase,
            BlockedRun(run="20261019T083000Z-4eba5e", question="Keep the guard of plan.py or drop it?"),
        )

    def test_should_carry_no_blocked_rebase_run_while_the_rebase_run_of_the_wave_branch_has_not_finished(self):
        # Arrange
        write_run(
            self.paths.state_root,
            {**create_run_record("20261019T083000Z-4eba5e", "w1", WAVE_BRANCH_RUN), "slot": "rebase"},
            None,
        )

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertIsNone(snapshot.waves[0].blocked_rebase)

    def test_should_carry_no_blocked_rebase_run_from_a_blocked_run_of_another_slot_on_the_wave_branch(self):
        # Arrange
        write_run(self.paths.state_root, create_run_record("20261019T083000Z-4eba5e", "w1", WAVE_BRANCH_RUN), None)
        self.record(
            5,
            dataclasses.replace(
                create_run_finished("20261019T083000Z-4eba5e", wave="w1", task=WAVE_BRANCH_RUN, outcome="blocked"),
                message=BLOCKED_REBASE_MESSAGE,
            ),
        )

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertIsNone(snapshot.waves[0].blocked_rebase)

    def test_should_carry_the_blocked_rebase_run_when_another_wave_is_paused_after_it(self):
        # Arrange
        self.record_rebase_run(WAVE_BRANCH_RUN, "blocked")
        self.record(4, WavePaused(wave="w0", reason="user", resume_at=None))

        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.waves[0].blocked_rebase,
            BlockedRun(run="20261019T083000Z-4eba5e", question="Keep the guard of plan.py or drop it?"),
        )


class BuildSnapshotOfAWaveOfQueuedTasksTest(BuildSnapshotTestCase):
    def test_should_read_no_pull_request_of_a_queued_task(self):
        # Arrange
        self.write_operational_corpus()
        self.record(60, WaveStarted(wave="w1", project="shop", branch="integration/w1", tasks=("B1", "B2", "B3", "B4")))

        # Act
        self.build()

        # Assert
        self.assertEqual(self.reader.branches, [])


class BuildSnapshotOfTheUncutMilestonesTest(BuildSnapshotTestCase):
    def setUp(self):
        super().setUp()
        self.write_operational_corpus()
        self.record(5, MilestoneBranchCut(project="shop", milestone="M2", branch="integration/tides", login=None))
        self.record(4, MilestoneClosed(project="shop", milestone="M2", pr=90))
        self.remote_answers = {
            **AWAWA_ANSWERS.answer_entities(
                self.main_tree,
                "MILESTONE",
                {
                    "M2": [{"name": "TITLE", "atoms": ['"Tides"']}],
                    "M3": [{"name": "TITLE", "atoms": ['"Dashboard"']}],
                    "M7": [{"name": "TITLE", "atoms": ['"Currents"']}],
                },
                "STATUS==active",
            ),
            **AWAWA_ANSWERS.answer_entities(
                self.main_tree,
                "TASK",
                {
                    "B8": [{"name": "MILESTONE", "atoms": ["@MILESTONE.M3"]}],
                    "B9": [{"name": "MILESTONE", "atoms": ["@MILESTONE.M2"]}],
                    "B10": [],
                },
                "STATUS==todo",
            ),
            **AWAWA_ANSWERS.answer_no_incoming_refs(self.main_tree, "B1", "B5"),
        }

    def test_should_list_the_active_milestones_at_main_that_no_branch_cut_records_with_their_todo_tasks(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(
            snapshot.projects[1].uncut_milestones,
            (
                UncutMilestone(milestone="M3", branch="integration/dashboard", todo=("B8",)),
                UncutMilestone(milestone="M7", branch="integration/currents", todo=()),
            ),
        )

    def test_should_list_none_for_a_paused_project(self):
        # Act
        snapshot, _ = self.build()

        # Assert
        self.assertEqual(snapshot.projects[0].uncut_milestones, ())
