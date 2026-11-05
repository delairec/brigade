import contextlib
import io
import json
import shutil
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.tick.read_integration_branches import (
    IntegrationBranchFacts,
    IntegrationBranchReading,
    read_integration_branches,
)
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

INSTANT = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
CUT_OF_M4 = LedgerEntry(
    instant=INSTANT,
    event=MilestoneBranchCut(project="shop", milestone="M4", branch="integration/tides", login="clauche-bot"),
)
CLOSE_OF_M4 = LedgerEntry(instant=INSTANT, event=MilestoneClosed(project="shop", milestone="M4", pr=90))
START_OF_W3 = LedgerEntry(
    instant=INSTANT,
    event=WaveStarted(wave="shop_w3", project="shop", tasks=("S5",), branch="integration/shop_w3"),
)
START_OF_W4_WITHOUT_BRANCH = LedgerEntry(
    instant=INSTANT, event=WaveStarted(wave="shop_w4", project="shop", tasks=("S6",))
)
CLOSE_OF_W3 = LedgerEntry(instant=INSTANT, event=WaveClosed(wave="shop_w3", pr=91))
CANCEL_OF_W3 = LedgerEntry(instant=INSTANT, event=WaveCancelled(wave="shop_w3", reason="the wave branch model ended"))
CUT_OF_ANOTHER_PROJECT = LedgerEntry(
    instant=INSTANT,
    event=MilestoneBranchCut(project="garden", milestone="M1", branch="integration/seeds", login="clauche-bot"),
)
TIDES_HEAD = ("git", "rev-parse", "--verify", "--quiet", "refs/heads/integration/tides")
W3_HEAD = ("git", "rev-parse", "--verify", "--quiet", "refs/heads/integration/shop_w3")
TIDES_IN_ITS_PULL_REQUEST = ("git", "merge-base", "--is-ancestor", "5ff69cd", "48537f8")
TIDES_IN_MAIN = ("git", "merge-base", "--is-ancestor", "5ff69cd", "main")
W3_IN_ITS_PULL_REQUEST = ("git", "merge-base", "--is-ancestor", "9c1e2d3", "48537f8")
W3_IN_ITS_MILESTONE_BRANCH = ("git", "merge-base", "--is-ancestor", "9c1e2d3", "integration/currents")
WORKTREE_LISTING = ("git", "worktree", "list", "--porcelain", "-z")


def create_pull_request(state: str) -> PullRequestFacts:
    return PullRequestFacts(
        number=90,
        state=state,
        checks=(),
        review=None,
        behind=False,
        head="48537f8",
        base="main",
        updated_at=datetime(2026, 11, 3, 8, 0, tzinfo=UTC),
    )


class PullRequestReaderDouble:
    def __init__(self, pull_requests: dict):
        self._pull_requests = pull_requests

    def __call__(self, repository: str, branch: str) -> PullRequestFacts | None:
        return self._pull_requests.get((repository, branch))


class ReadIntegrationBranchesTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.repository = self.root / "shop"
        self.tides_worktree = self.repository / ".brigade" / "worktrees" / "integration-tides"
        self.w3_worktree = self.repository / ".brigade" / "worktrees" / "integration-shop_w3"
        self.state_root = self.root / "state"
        self.shop = Entity(
            name="shop",
            fields=(EntityField(name="PATH", value=str(self.repository)), EntityField(name="MAIN", value="main")),
        )

    def create_reading(self, entries: tuple, pull_requests: dict) -> IntegrationBranchReading:
        return IntegrationBranchReading(
            entries=entries,
            projects=(self.shop,),
            worktree_root=None,
            state_root=self.state_root,
            read_pull_request=PullRequestReaderDouble(pull_requests),
            read_environment=lambda slot: {},
            locate_wave_base=lambda started: "integration/currents",
            is_alive=lambda run_directory: True,
        )

    def record_run_on(self, worktree: Path) -> None:
        run = self.state_root / "runs" / "20261105T150000Z-afb9db"
        run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"cwd": str(worktree)}), encoding="utf-8")


class ReadMilestoneBranchesTest(ReadIntegrationBranchesTestCase):
    def test_should_read_a_closed_milestone_branch_with_its_merged_pull_request_and_its_worktree(self):
        # Arrange
        self.tides_worktree.mkdir(parents=True)
        git = RecordingProcessRunner({TIDES_HEAD: ProcessAnswer(stdout="5ff69cd\n")})
        reading = self.create_reading(
            (CUT_OF_M4, CLOSE_OF_M4),
            {(str(self.repository), "integration/tides"): create_pull_request("merged")},
        )

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertEqual(
            branches,
            (
                IntegrationBranchFacts(
                    project="shop",
                    branch="integration/tides",
                    milestone="M4",
                    wave=None,
                    ended=True,
                    merged_pull_request=90,
                    merged_head="48537f8",
                    head="5ff69cd",
                    reached_forge=True,
                    worktree=str(self.tides_worktree),
                    run_live=False,
                    locked=False,
                ),
            ),
        )

    def test_should_read_an_active_milestone_branch_whose_pull_request_is_open_as_heading_no_merged_one(self):
        # Arrange
        git = RecordingProcessRunner(
            {TIDES_HEAD: ProcessAnswer(stdout="5ff69cd\n"), TIDES_IN_MAIN: ProcessAnswer(exit_code=1)}
        )
        reading = self.create_reading(
            (CUT_OF_M4,), {(str(self.repository), "integration/tides"): create_pull_request("open")}
        )

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertEqual(
            branches,
            (
                IntegrationBranchFacts(
                    project="shop",
                    branch="integration/tides",
                    milestone="M4",
                    wave=None,
                    ended=False,
                    merged_pull_request=None,
                    merged_head=None,
                    head="5ff69cd",
                    reached_forge=False,
                    worktree=None,
                    run_live=False,
                    locked=False,
                ),
            ),
        )

    def test_should_read_no_branch_that_does_not_stand_locally(self):
        # Arrange
        git = RecordingProcessRunner({TIDES_HEAD: ProcessAnswer(exit_code=1)})
        reading = self.create_reading((CUT_OF_M4, CLOSE_OF_M4), {})

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertEqual(branches, ())

    def test_should_read_no_branch_of_a_project_it_does_not_read(self):
        # Arrange
        git = RecordingProcessRunner()
        reading = self.create_reading((CUT_OF_ANOTHER_PROJECT,), {})

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertEqual(branches, ())


class ReadTheForgeReachOfABranchTest(ReadIntegrationBranchesTestCase):
    def test_should_tell_whether_the_local_head_is_within_the_merged_pull_request(self):
        for exit_code, reached_forge in [(0, True), (1, False)]:
            with self.subTest(exit_code=exit_code):
                # Arrange
                git = RecordingProcessRunner(
                    {
                        TIDES_HEAD: ProcessAnswer(stdout="5ff69cd\n"),
                        TIDES_IN_ITS_PULL_REQUEST: ProcessAnswer(exit_code=exit_code),
                        TIDES_IN_MAIN: ProcessAnswer(exit_code=1),
                    }
                )
                reading = self.create_reading(
                    (CUT_OF_M4, CLOSE_OF_M4),
                    {(str(self.repository), "integration/tides"): create_pull_request("merged")},
                )

                # Act
                branches = read_integration_branches(git, reading)

                # Assert
                self.assertEqual(branches[0].reached_forge, reached_forge)

    def test_should_tell_whether_the_local_head_of_a_milestone_branch_is_within_the_main_branch(self):
        for exit_code, reached_forge in [(0, True), (1, False)]:
            with self.subTest(exit_code=exit_code):
                # Arrange
                git = RecordingProcessRunner(
                    {
                        TIDES_HEAD: ProcessAnswer(stdout="5ff69cd\n"),
                        TIDES_IN_ITS_PULL_REQUEST: ProcessAnswer(exit_code=1),
                        TIDES_IN_MAIN: ProcessAnswer(exit_code=exit_code),
                    }
                )
                reading = self.create_reading(
                    (CUT_OF_M4, CLOSE_OF_M4),
                    {(str(self.repository), "integration/tides"): create_pull_request("merged")},
                )

                # Act
                branches = read_integration_branches(git, reading)

                # Assert
                self.assertEqual(branches[0].reached_forge, reached_forge)

    def test_should_compare_a_wave_branch_to_the_branch_of_its_milestone(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                W3_HEAD: ProcessAnswer(stdout="9c1e2d3\n"),
                W3_IN_ITS_MILESTONE_BRANCH: ProcessAnswer(),
            }
        )
        reading = self.create_reading((START_OF_W3, CANCEL_OF_W3), {})

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertEqual(
            branches,
            (
                IntegrationBranchFacts(
                    project="shop",
                    branch="integration/shop_w3",
                    milestone=None,
                    wave="shop_w3",
                    ended=True,
                    merged_pull_request=None,
                    merged_head=None,
                    head="9c1e2d3",
                    reached_forge=True,
                    worktree=None,
                    run_live=False,
                    locked=False,
                ),
            ),
        )

    def test_should_tell_a_cancelled_wave_branch_holding_a_commit_of_its_own_outside_the_forge(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                W3_HEAD: ProcessAnswer(stdout="9c1e2d3\n"),
                W3_IN_ITS_MILESTONE_BRANCH: ProcessAnswer(exit_code=1),
            }
        )
        reading = self.create_reading((START_OF_W3, CANCEL_OF_W3), {})

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertFalse(branches[0].reached_forge)


class ReadWaveBranchesTest(ReadIntegrationBranchesTestCase):
    def test_should_tell_whether_the_wave_of_a_branch_has_ended(self):
        for entries, ended in [
            ((START_OF_W3,), False),
            ((START_OF_W3, CLOSE_OF_W3), True),
            ((START_OF_W3, CANCEL_OF_W3), True),
        ]:
            with self.subTest(entries=entries):
                # Arrange
                git = RecordingProcessRunner({W3_HEAD: ProcessAnswer(stdout="9c1e2d3\n")})
                reading = self.create_reading(entries, {})

                # Act
                branches = read_integration_branches(git, reading)

                # Assert
                self.assertEqual(branches[0].ended, ended)

    def test_should_read_no_branch_of_a_wave_started_without_one(self):
        # Arrange
        git = RecordingProcessRunner()
        reading = self.create_reading((START_OF_W4_WITHOUT_BRANCH,), {})

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertEqual(branches, ())


class ReadTheWorktreeOfABranchTest(ReadIntegrationBranchesTestCase):
    def test_should_tell_that_a_run_is_live_on_the_worktree_of_the_branch(self):
        # Arrange
        self.w3_worktree.mkdir(parents=True)
        self.record_run_on(self.w3_worktree)
        git = RecordingProcessRunner({W3_HEAD: ProcessAnswer(stdout="9c1e2d3\n")})
        reading = self.create_reading((START_OF_W3, CLOSE_OF_W3), {})

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertTrue(branches[0].run_live)

    def test_should_tell_that_git_lists_the_worktree_of_the_branch_locked(self):
        # Arrange
        self.w3_worktree.mkdir(parents=True)
        listing = (
            f"worktree {self.repository}\0HEAD 1a2b3c4\0branch refs/heads/main\0\0"
            f"worktree {self.w3_worktree}\0HEAD 9c1e2d3\0branch refs/heads/integration/shop_w3\0locked held\0\0"
        )
        git = RecordingProcessRunner(
            {W3_HEAD: ProcessAnswer(stdout="9c1e2d3\n"), WORKTREE_LISTING: ProcessAnswer(stdout=listing)}
        )
        reading = self.create_reading((START_OF_W3, CLOSE_OF_W3), {})

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertTrue(branches[0].locked)

    def test_should_tell_no_lock_on_a_worktree_git_lists_unlocked(self):
        # Arrange
        self.w3_worktree.mkdir(parents=True)
        listing = (
            f"worktree {self.w3_worktree}\0HEAD 9c1e2d3\0branch refs/heads/integration/shop_w3\0\0"
            f"worktree {self.repository / 'other'}\0HEAD 1a2b3c4\0branch refs/heads/other\0locked held\0\0"
        )
        git = RecordingProcessRunner(
            {W3_HEAD: ProcessAnswer(stdout="9c1e2d3\n"), WORKTREE_LISTING: ProcessAnswer(stdout=listing)}
        )
        reading = self.create_reading((START_OF_W3, CLOSE_OF_W3), {})

        # Act
        branches = read_integration_branches(git, reading)

        # Assert
        self.assertFalse(branches[0].locked)


class ReadABranchItCannotReadTest(ReadIntegrationBranchesTestCase):
    def test_should_skip_the_branch_whose_facts_git_refuses_and_read_the_others(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                TIDES_HEAD: ProcessAnswer(stdout="5ff69cd\n"),
                TIDES_IN_ITS_PULL_REQUEST: ProcessAnswer(exit_code=128, stderr="fatal: bad object 48537f8"),
                W3_HEAD: ProcessAnswer(stdout="9c1e2d3\n"),
            }
        )
        reading = self.create_reading(
            (CUT_OF_M4, CLOSE_OF_M4, START_OF_W3, CLOSE_OF_W3),
            {(str(self.repository), "integration/tides"): create_pull_request("merged")},
        )

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            branches = read_integration_branches(git, reading)

        # Assert
        self.assertEqual(branches[0].branch, "integration/shop_w3")

    def test_should_name_the_branch_it_skips_on_stderr(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                TIDES_HEAD: ProcessAnswer(stdout="5ff69cd\n"),
                TIDES_IN_ITS_PULL_REQUEST: ProcessAnswer(exit_code=128, stderr="fatal: bad object 48537f8"),
            }
        )
        reading = self.create_reading(
            (CUT_OF_M4, CLOSE_OF_M4),
            {(str(self.repository), "integration/tides"): create_pull_request("merged")},
        )
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            read_integration_branches(git, reading)

        # Assert
        self.assertIn("brigade tick: the branch integration/tides of shop skipped: ", errors.getvalue())


class IntegrationBranchFactsTest(unittest.TestCase):
    def test_should_carry_its_facts_in_its_document(self):
        # Arrange
        facts = IntegrationBranchFacts(
            project="shop",
            branch="integration/tides",
            milestone="M4",
            wave=None,
            ended=True,
            merged_pull_request=90,
            merged_head="48537f8",
            head="5ff69cd",
            reached_forge=True,
            worktree="/srv/shop/.brigade/worktrees/integration-tides",
            run_live=False,
            locked=True,
        )

        # Act
        document = facts.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "project": "shop",
                "branch": "integration/tides",
                "milestone": "M4",
                "wave": None,
                "ended": True,
                "merged_pull_request": 90,
                "merged_head": "48537f8",
                "head": "5ff69cd",
                "reached_forge": True,
                "worktree": "/srv/shop/.brigade/worktrees/integration-tides",
                "run_live": False,
                "locked": True,
            },
        )
