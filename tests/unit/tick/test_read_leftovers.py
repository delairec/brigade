import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import CommandFailed
from brigade.tick.read_leftovers import LeftoverFacts, LeftoverReading, read_leftovers
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

WORKTREE_LISTING = ("git", "worktree", "list", "--porcelain", "-z")
LOCAL_BRANCHES_LISTING = ("git", "for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads")
SPROUT_HEAD = ("git", "rev-parse", "--verify", "--quiet", "refs/heads/feature/S7-sprout")
SPROUT_IN_ITS_PULL_REQUEST = ("git", "merge-base", "--is-ancestor", "c0ffee1", "c0ffee9")
SPROUT_ON_A_REMOTE = (
    "git",
    "for-each-ref",
    "--count=1",
    "--contains",
    "c0ffee1",
    "--format=%(refname)",
    "refs/remotes",
)
DETACHED_ON_A_REMOTE = (
    "git",
    "for-each-ref",
    "--count=1",
    "--contains",
    "d00d1e2",
    "--format=%(refname)",
    "refs/remotes",
)
LOCAL_CHANGES = ("git", "status", "--porcelain")
SPROUT_PULL_REQUEST_HEAD = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "c0ffee9^{commit}")
STALE_SPROUT = {
    "branch": "feature/S7-sprout",
    "pull_requests": [{"number": 7, "state": "merged", "head_sha": "c0ffee9"}],
}


class StaleBranchesReaderDouble:
    def __init__(self, stale: list[dict]):
        self._stale = stale

    def __call__(self, project: Entity) -> list[dict]:
        return self._stale


class FailingStaleBranchesReaderDouble:
    def __call__(self, project: Entity) -> list[dict]:
        raise CommandFailed(("gh", "api", "graphql"), 1, "HTTP 502")


class ReadLeftoversTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.repository = self.root / "shop"
        self.sprout = self.repository / ".brigade" / "worktrees" / "S7"
        self.state_root = self.root / "state"
        self.shop = Entity(
            name="shop",
            fields=(EntityField(name="PATH", value=str(self.repository)), EntityField(name="MAIN", value="main")),
        )

    def create_reading(self, stale: list[dict], excluded: frozenset = frozenset()) -> LeftoverReading:
        return LeftoverReading(
            projects=(self.shop,),
            excluded_branches=excluded,
            state_root=self.state_root,
            is_alive=lambda run_directory: True,
            read_stale_branches=StaleBranchesReaderDouble(stale),
        )

    def list_worktrees(self, *records: str) -> ProcessAnswer:
        return ProcessAnswer(stdout="\0\0".join(records) + "\0\0")

    def main_checkout_on(self, branch: str) -> str:
        return f"worktree {self.repository}\0HEAD a0a0a0a\0branch refs/heads/{branch}"


class ReadAStaleBranchTest(ReadLeftoversTestCase):
    def test_should_read_a_stale_branch_with_its_worktree(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                WORKTREE_LISTING: self.list_worktrees(
                    self.main_checkout_on("main"),
                    f"worktree {self.sprout}\0HEAD c0ffee1\0branch refs/heads/feature/S7-sprout",
                ),
                LOCAL_BRANCHES_LISTING: ProcessAnswer(stdout="main\nfeature/S7-sprout\n"),
                SPROUT_HEAD: ProcessAnswer(stdout="c0ffee1\n"),
                SPROUT_PULL_REQUEST_HEAD: ProcessAnswer(stdout="c0ffee9\n"),
            }
        )

        # Act
        leftovers = read_leftovers(git, self.create_reading([STALE_SPROUT]))

        # Assert
        self.assertEqual(
            leftovers,
            (
                LeftoverFacts(
                    project="shop",
                    branch="feature/S7-sprout",
                    worktree=str(self.sprout),
                    head="c0ffee1",
                    reached_forge=True,
                    run_live=False,
                    locked=False,
                    uncommitted=False,
                    main_checkout=False,
                ),
            ),
        )

    def test_should_tell_whether_the_head_of_a_stale_branch_reached_the_forge(self):
        for within_its_pull_request, on_a_remote, reached_forge in [
            (0, "", True),
            (1, "refs/remotes/origin/main\n", True),
            (1, "", False),
        ]:
            with self.subTest(within_its_pull_request=within_its_pull_request, on_a_remote=on_a_remote):
                # Arrange
                git = RecordingProcessRunner(
                    {
                        WORKTREE_LISTING: self.list_worktrees(self.main_checkout_on("main")),
                        SPROUT_HEAD: ProcessAnswer(stdout="c0ffee1\n"),
                        SPROUT_PULL_REQUEST_HEAD: ProcessAnswer(stdout="c0ffee9\n"),
                        SPROUT_IN_ITS_PULL_REQUEST: ProcessAnswer(exit_code=within_its_pull_request),
                        SPROUT_ON_A_REMOTE: ProcessAnswer(stdout=on_a_remote),
                    }
                )

                # Act
                leftovers = read_leftovers(git, self.create_reading([STALE_SPROUT]))

                # Assert
                self.assertEqual(leftovers[0].reached_forge, reached_forge)

    def test_should_read_the_guards_of_the_worktree_of_a_stale_branch(self):
        # Arrange
        run = self.state_root / "runs" / "20261114T100000Z-a1b2c3"
        run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"cwd": str(self.sprout)}), encoding="utf-8")
        self.sprout.mkdir(parents=True)
        git = RecordingProcessRunner(
            {
                WORKTREE_LISTING: self.list_worktrees(
                    self.main_checkout_on("main"),
                    f"worktree {self.sprout}\0HEAD c0ffee1\0branch refs/heads/feature/S7-sprout\0locked",
                ),
                SPROUT_HEAD: ProcessAnswer(stdout="c0ffee1\n"),
                SPROUT_PULL_REQUEST_HEAD: ProcessAnswer(stdout="c0ffee9\n"),
                LOCAL_CHANGES: ProcessAnswer(stdout=" M brigade/tick/plan.py\n"),
            }
        )

        # Act
        leftovers = read_leftovers(git, self.create_reading([STALE_SPROUT]))

        # Assert
        self.assertEqual(
            leftovers,
            (
                LeftoverFacts(
                    project="shop",
                    branch="feature/S7-sprout",
                    worktree=str(self.sprout),
                    head="c0ffee1",
                    reached_forge=True,
                    run_live=True,
                    locked=True,
                    uncommitted=True,
                    main_checkout=False,
                ),
            ),
        )

    def test_should_read_a_stale_branch_the_main_checkout_holds(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                WORKTREE_LISTING: self.list_worktrees(self.main_checkout_on("feature/S7-sprout")),
                SPROUT_HEAD: ProcessAnswer(stdout="c0ffee1\n"),
            }
        )

        # Act
        leftovers = read_leftovers(git, self.create_reading([STALE_SPROUT]))

        # Assert
        self.assertEqual(leftovers[0].main_checkout, True)

    def test_should_read_a_worktree_holding_only_untracked_files_as_holding_uncommitted_changes(self):
        # Arrange
        self.sprout.mkdir(parents=True)
        git = RecordingProcessRunner(
            {
                WORKTREE_LISTING: self.list_worktrees(
                    self.main_checkout_on("main"),
                    f"worktree {self.sprout}\0HEAD c0ffee1\0branch refs/heads/feature/S7-sprout",
                ),
                SPROUT_HEAD: ProcessAnswer(stdout="c0ffee1\n"),
                LOCAL_CHANGES: ProcessAnswer(stdout="?? notes/draft.md\n"),
            }
        )

        # Act
        leftovers = read_leftovers(git, self.create_reading([STALE_SPROUT]))

        # Assert
        self.assertEqual(leftovers[0].uncommitted, True)

    def test_should_read_a_locked_worktree_whose_directory_is_gone_without_running_git_in_it(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                WORKTREE_LISTING: self.list_worktrees(
                    self.main_checkout_on("main"),
                    f"worktree {self.sprout}\0HEAD c0ffee1\0branch refs/heads/feature/S7-sprout\0locked",
                ),
                SPROUT_HEAD: ProcessAnswer(stdout="c0ffee1\n"),
                SPROUT_PULL_REQUEST_HEAD: ProcessAnswer(stdout="c0ffee9\n"),
                LOCAL_CHANGES: ProcessAnswer(stdout=" M brigade/tick/plan.py\n"),
            }
        )

        # Act
        leftovers = read_leftovers(git, self.create_reading([STALE_SPROUT]))

        # Assert
        self.assertEqual(
            leftovers,
            (
                LeftoverFacts(
                    project="shop",
                    branch="feature/S7-sprout",
                    worktree=str(self.sprout),
                    head="c0ffee1",
                    reached_forge=True,
                    run_live=False,
                    locked=True,
                    uncommitted=False,
                    main_checkout=False,
                ),
            ),
        )

    def test_should_read_a_pull_request_head_the_clone_never_fetched_as_not_holding_the_branch_head(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                WORKTREE_LISTING: self.list_worktrees(self.main_checkout_on("main")),
                SPROUT_HEAD: ProcessAnswer(stdout="c0ffee1\n"),
                SPROUT_PULL_REQUEST_HEAD: ProcessAnswer(exit_code=1),
                SPROUT_IN_ITS_PULL_REQUEST: ProcessAnswer(
                    exit_code=128, stderr="fatal: Not a valid commit name c0ffee9"
                ),
            }
        )

        # Act
        leftovers = read_leftovers(git, self.create_reading([STALE_SPROUT]))

        # Assert
        self.assertEqual(leftovers[0].reached_forge, False)

    def test_should_read_no_stale_branch_the_ledger_records_as_an_integration_branch(self):
        # Arrange
        git = RecordingProcessRunner({WORKTREE_LISTING: self.list_worktrees(self.main_checkout_on("main"))})
        reading = self.create_reading([STALE_SPROUT], excluded=frozenset({("shop", "feature/S7-sprout")}))

        # Act
        leftovers = read_leftovers(git, reading)

        # Assert
        self.assertEqual(leftovers, ())


class ReadAStaleWorktreeTest(ReadLeftoversTestCase):
    def test_should_read_a_detached_worktree_without_a_live_run_as_a_worktree_alone(self):
        # Arrange
        detached = self.repository / ".brigade" / "worktrees" / "S8"
        git = RecordingProcessRunner(
            {
                WORKTREE_LISTING: self.list_worktrees(
                    self.main_checkout_on("main"), f"worktree {detached}\0HEAD d00d1e2\0detached"
                ),
                LOCAL_BRANCHES_LISTING: ProcessAnswer(stdout="main\n"),
                DETACHED_ON_A_REMOTE: ProcessAnswer(stdout="refs/remotes/origin/main\n"),
            }
        )
        reading = LeftoverReading(
            projects=(self.shop,),
            excluded_branches=frozenset(),
            state_root=self.state_root,
            is_alive=lambda run_directory: False,
            read_stale_branches=StaleBranchesReaderDouble([]),
        )

        # Act
        leftovers = read_leftovers(git, reading)

        # Assert
        self.assertEqual(
            leftovers,
            (
                LeftoverFacts(
                    project="shop",
                    branch=None,
                    worktree=str(detached),
                    head="d00d1e2",
                    reached_forge=True,
                    run_live=False,
                    locked=False,
                    uncommitted=False,
                    main_checkout=False,
                ),
            ),
        )


class ReadTheLeftoversOfAProjectItCannotReadTest(ReadLeftoversTestCase):
    def test_should_name_on_stderr_the_project_whose_leftovers_it_skips(self):
        # Arrange
        git = RecordingProcessRunner({WORKTREE_LISTING: self.list_worktrees(self.main_checkout_on("main"))})
        reading = LeftoverReading(
            projects=(self.shop,),
            excluded_branches=frozenset(),
            state_root=self.state_root,
            is_alive=lambda run_directory: False,
            read_stale_branches=FailingStaleBranchesReaderDouble(),
        )
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            leftovers = read_leftovers(git, reading)

        # Assert
        self.assertEqual(leftovers, ())
        self.assertRegex(errors.getvalue(), "^brigade tick: the leftovers of shop skipped: ")


class LeftoverFactsTest(unittest.TestCase):
    def test_should_carry_its_facts_in_its_document(self):
        # Arrange
        facts = LeftoverFacts(
            project="shop",
            branch="feature/S7-sprout",
            worktree="/srv/shop/.brigade/worktrees/S7",
            head="c0ffee1",
            reached_forge=True,
            run_live=False,
            locked=True,
            uncommitted=False,
            main_checkout=False,
        )

        # Act
        document = facts.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "project": "shop",
                "branch": "feature/S7-sprout",
                "worktree": "/srv/shop/.brigade/worktrees/S7",
                "head": "c0ffee1",
                "reached_forge": True,
                "run_live": False,
                "locked": True,
                "uncommitted": False,
                "main_checkout": False,
            },
        )
