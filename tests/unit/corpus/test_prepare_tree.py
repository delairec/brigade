import io
import os
import shutil
import tarfile
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.prepare_tree import Tree, TreeRequest, prepare_tree
from brigade.errors import BrigadeError, CannotWrite
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
LONG_AGO = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
WORKTREES = (
    "worktree /srv/shop\0HEAD 1111111\0branch refs/heads/main\0\0"
    "worktree /srv/worktrees/b42\0HEAD 2222222\0branch refs/heads/feat/b42\0\0"
)
README = ("README.md", b"# shop\n")
RUNNING_AS_ROOT = os.geteuid() == 0


def write_archive(destination: Path, members: list[tuple[str, bytes]]) -> None:
    with tarfile.open(destination, "w") as archive:
        for name, content in members:
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))


class ArchivingGit(RecordingProcessRunner):
    def __init__(self, sha: str, members: list[tuple[str, bytes]]):
        super().__init__(
            {
                ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "v1^{commit}"): ProcessAnswer(
                    stdout=f"{sha}\n"
                ),
                ("git", "worktree", "list", "--porcelain", "-z"): ProcessAnswer(stdout=WORKTREES),
            }
        )
        self.members = members
        self.placed_meanwhile = []

    def __call__(self, request):
        record = super().__call__(request)
        if request.argv[1] == "archive":
            write_archive(Path(request.argv[3].removeprefix("--output=")), self.members)
            for placed in self.placed_meanwhile:
                placed.mkdir(parents=True)
        return record


class PrepareTreeTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.cache = self.root / "refs"

    def create_request(self, ref: str | None, worktree: Path | None = None, **changes) -> TreeRequest:
        return TreeRequest(
            **{
                "project": "shop",
                "repository": Path("/srv/shop"),
                "ref": ref,
                "worktree": worktree,
                "cache": self.cache,
                "cache_bound_bytes": 1024,
                "cache_lock": self.root / "locks" / "refs-cache.lock",
                "now": NOW,
                **changes,
            }
        )

    def lock_directory(self, directory: Path, mode: int) -> None:
        directory.chmod(mode)
        self.addCleanup(directory.chmod, 0o700)


class PrepareTreeOfAWorktreeTest(PrepareTreeTestCase):
    def test_should_answer_the_worktree_at_the_path_or_holding_the_branch(self):
        for ref, worktree in [(None, Path("/srv/worktrees/b42")), ("worktree:feat/b42", None)]:
            with self.subTest(ref=ref):
                # Act
                tree = prepare_tree(ArchivingGit("abc", []), self.create_request(ref, worktree))

                # Assert
                self.assertEqual(
                    tree, Tree(project="shop", ref=ref, sha="2222222", kind="worktree", root=Path("/srv/worktrees/b42"))
                )

    def test_should_refuse_a_worktree_the_repository_does_not_hold(self):
        for ref, worktree, message in [
            (None, Path("/srv/worktrees/b43"), "no worktree of @PROJECT.shop is at /srv/worktrees/b43"),
            ("worktree:feat/b43", None, "no worktree of @PROJECT.shop has the branch feat/b43 checked out"),
        ]:
            with self.subTest(ref=ref):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    prepare_tree(ArchivingGit("abc", []), self.create_request(ref, worktree))

                # Assert
                self.assertEqual(str(refusal.exception), message)


class PrepareTreeOfACommitTest(PrepareTreeTestCase):
    def test_should_extract_the_commit_into_the_cache(self):
        # Act
        tree = prepare_tree(ArchivingGit("abc123", [README]), self.create_request("v1"))

        # Assert
        self.assertEqual(
            (tree, (self.cache / "shop" / "abc123" / "README.md").read_text(), [p.name for p in self.cache.iterdir()]),
            (
                Tree(project="shop", ref="v1", sha="abc123", kind="archive", root=self.cache / "shop" / "abc123"),
                "# shop\n",
                ["shop"],
            ),
        )

    def test_should_reuse_the_tree_already_cached_and_mark_it_read(self):
        # Arrange
        cached = self.cache / "shop" / "abc123"
        cached.mkdir(parents=True)
        os.utime(cached, (LONG_AGO.timestamp(), LONG_AGO.timestamp()))
        git = ArchivingGit("abc123", [README])

        # Act
        prepare_tree(git, self.create_request("v1"))

        # Assert
        self.assertEqual(
            ([argv[1] for _, argv in git.commands], cached.stat().st_mtime), (["rev-parse"], NOW.timestamp())
        )

    def test_should_evict_the_trees_read_longest_ago_beyond_the_bound(self):
        # Arrange
        stale = self.cache / "tidepool" / "old999"
        stale.mkdir(parents=True)
        (stale / "big.bin").write_bytes(b"x" * 2048)
        os.utime(stale, (LONG_AGO.timestamp(), LONG_AGO.timestamp()))
        (self.cache / ".removing").mkdir()

        # Act
        prepare_tree(ArchivingGit("abc123", [README]), self.create_request("v1"))

        # Assert
        self.assertEqual((stale.exists(), (self.cache / "shop" / "abc123").exists()), (False, True))

    def test_should_refuse_a_ref_naming_no_commit(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_tree(ArchivingGit("", [README]), self.create_request("v1"))

        # Assert
        self.assertEqual(str(refusal.exception), "the ref v1 is not a commit of @PROJECT.shop")

    def test_should_refuse_an_archive_holding_a_member_outside_the_tree(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_tree(ArchivingGit("abc123", [("../evil", b"x")]), self.create_request("v1"))

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the archive of @PROJECT.shop holds ../evil, a member tarfile's data filter refuses",
        )

    def test_should_keep_the_tree_another_extraction_placed_meanwhile(self):
        # Arrange
        git = ArchivingGit("abc123", [README])
        git.placed_meanwhile.append(self.cache / "shop" / "abc123")

        # Act
        tree = prepare_tree(git, self.create_request("v1"))

        # Assert
        self.assertEqual(list(tree.root.iterdir()), [])

    def test_should_stop_evicting_once_the_cache_is_back_within_its_bound(self):
        # Arrange
        oldest = self.cache / "tidepool" / "old111"
        older = self.cache / "tidepool" / "old222"
        for tree, kept_bytes, read_at in [(oldest, 2048, LONG_AGO), (older, 8, NOW.replace(month=6))]:
            tree.mkdir(parents=True)
            (tree / "file.bin").write_bytes(b"x" * kept_bytes)
            os.utime(tree, (read_at.timestamp(), read_at.timestamp()))

        # Act
        prepare_tree(ArchivingGit("abc123", [README]), self.create_request("v1"))

        # Assert
        self.assertEqual((oldest.exists(), older.exists()), (False, True))


@unittest.skipIf(RUNNING_AS_ROOT, "root writes through every permission")
class PrepareTreeThatCannotWriteTest(PrepareTreeTestCase):
    def test_should_refuse_a_project_cache_it_cannot_stage_in(self):
        # Arrange
        (self.cache / "shop").mkdir(parents=True)
        self.lock_directory(self.cache / "shop", 0o500)

        # Act / Assert
        with self.assertRaises(CannotWrite):
            prepare_tree(ArchivingGit("abc123", [README]), self.create_request("v1"))

    def test_should_refuse_an_archive_it_cannot_unpack(self):
        # Act / Assert
        with self.assertRaises(CannotWrite):
            prepare_tree(ArchivingGit("abc123", [("a", b"x"), ("a/b", b"y")]), self.create_request("v1"))

    def test_should_refuse_a_tree_place_a_file_holds(self):
        # Arrange
        (self.cache / "shop").mkdir(parents=True)
        (self.cache / "shop" / "abc123").write_text("not a tree")

        # Act / Assert
        with self.assertRaises(CannotWrite):
            prepare_tree(ArchivingGit("abc123", [README]), self.create_request("v1"))

    def test_should_refuse_a_cached_tree_it_cannot_mark_read(self):
        # Arrange
        root_owned = self.create_request("v1", project="usr", cache=Path("/"))

        # Act / Assert
        with self.assertRaises(CannotWrite):
            prepare_tree(ArchivingGit("bin", [README]), root_owned)

    def test_should_refuse_a_cache_it_cannot_list(self):
        # Arrange
        (self.cache / "tidepool").mkdir(parents=True)
        self.lock_directory(self.cache / "tidepool", 0o000)

        # Act / Assert
        with self.assertRaises(CannotWrite):
            prepare_tree(ArchivingGit("abc123", [README]), self.create_request("v1"))

    def test_should_refuse_a_stale_tree_it_cannot_evict(self):
        # Arrange
        stale = self.cache / "tidepool" / "old999"
        stale.mkdir(parents=True)
        (stale / "big.bin").write_bytes(b"x" * 2048)
        self.lock_directory(self.cache / "tidepool", 0o500)

        # Act / Assert
        with self.assertRaises(CannotWrite):
            prepare_tree(ArchivingGit("abc123", [README]), self.create_request("v1"))
