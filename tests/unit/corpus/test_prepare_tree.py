import errno
import io
import os
import shutil
import tarfile
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.prepare_tree import FILESYSTEM_READ_TIME_KEEPER, Tree, TreeRequest, prepare_tree
from brigade.errors import BrigadeError, CannotWrite
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
LONG_AGO = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
LAST_JUNE = datetime(2026, 6, 19, 9, 0, tzinfo=UTC)
WORKTREES = (
    "worktree /srv/shop\0HEAD 1111111\0branch refs/heads/main\0\0"
    "worktree /srv/worktrees/b42\0HEAD 2222222\0branch refs/heads/feat/b42\0\0"
)
README = ("README.md", b"# shop\n")
LONGEST_PATH = 4095
PADDING_NAME = "p" * 149
NAME_LONGER_THAN_ITS_EVICTION_ALLOWS = "s" * 230


def write_archive(destination: Path, members: list[tuple[str, bytes]]) -> None:
    with tarfile.open(destination, "w") as archive:
        for name, content in members:
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))


def create_path_of_length(base: Path, length: int) -> Path:
    padding = length - len(str(base))
    whole_names = (padding - 100) // (len(PADDING_NAME) + 1)
    last_name = "q" * (padding - whole_names * (len(PADDING_NAME) + 1) - 1)
    return base.joinpath(*[PADDING_NAME] * whole_names, last_name)


def write_tree(tree: Path, size_bytes: int, read_at: datetime) -> None:
    tree.mkdir(parents=True)
    (tree / "file.bin").write_bytes(b"x" * size_bytes)
    os.utime(tree, (read_at.timestamp(), read_at.timestamp()))


def refuse_to_stamp(tree: Path, read_ns: int) -> None:
    raise PermissionError(errno.EPERM, "Operation not permitted", str(tree))


def create_refusing_stamp_reader(refusal: OSError) -> Callable[[Path], int]:
    def read_stamp(tree: Path) -> int:
        raise refusal

    return read_stamp


class ArchivingGitDouble(RecordingProcessRunner):
    def __init__(self, sha: str, members: list[tuple[str, bytes]], placed_meanwhile: Path | None = None):
        super().__init__(
            {
                ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "v1^{commit}"): ProcessAnswer(
                    stdout=f"{sha}\n"
                ),
                ("git", "worktree", "list", "--porcelain", "-z"): ProcessAnswer(stdout=WORKTREES),
            }
        )
        self.members = members
        self.placed_meanwhile = placed_meanwhile

    def __call__(self, request):
        record = super().__call__(request)
        if request.argv[1] == "archive":
            write_archive(Path(request.argv[3].removeprefix("--output=")), self.members)
            if self.placed_meanwhile is not None:
                self.placed_meanwhile.mkdir(parents=True)
        return record


class PrepareTreeTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.cache = self.root / "refs"

    def create_request(self, ref: str | None, worktree: Path | None = None, cache: Path | None = None) -> TreeRequest:
        return TreeRequest(
            project="shop",
            repository=Path("/srv/shop"),
            ref=ref,
            worktree=worktree,
            cache=self.cache if cache is None else cache,
            cache_bound_bytes=1024,
            cache_lock=self.root / "locks" / "refs-cache.lock",
            now=NOW,
        )


class PrepareTreeOfAWorktreeTest(PrepareTreeTestCase):
    def test_should_answer_the_worktree_at_the_path_or_holding_the_branch(self):
        for ref, worktree in [(None, Path("/srv/worktrees/b42")), ("worktree:feat/b42", None)]:
            with self.subTest(ref=ref):
                # Act
                tree = prepare_tree(
                    ArchivingGitDouble("abc", []), FILESYSTEM_READ_TIME_KEEPER, self.create_request(ref, worktree)
                )

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
                    prepare_tree(
                        ArchivingGitDouble("abc", []), FILESYSTEM_READ_TIME_KEEPER, self.create_request(ref, worktree)
                    )

                # Assert
                self.assertEqual(str(refusal.exception), message)


class PrepareTreeOfACommitTest(PrepareTreeTestCase):
    def test_should_extract_the_commit_into_the_cache(self):
        # Act
        tree = prepare_tree(
            ArchivingGitDouble("abc123", [README]), FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1")
        )

        # Assert
        self.assertEqual(
            tree, Tree(project="shop", ref="v1", sha="abc123", kind="archive", root=self.cache / "shop" / "abc123")
        )
        self.assertEqual((self.cache / "shop" / "abc123" / "README.md").read_text(), "# shop\n")
        self.assertEqual(list(self.cache.iterdir()), [self.cache / "shop"])

    def test_should_reuse_the_tree_already_cached_and_mark_it_read(self):
        # Arrange
        cached = self.cache / "shop" / "abc123"
        write_tree(cached, 8, LONG_AGO)
        git = ArchivingGitDouble("abc123", [README])

        # Act
        prepare_tree(git, FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1"))

        # Assert
        self.assertEqual(
            git.commands,
            [("/srv/shop", ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "v1^{commit}"))],
        )
        self.assertEqual(cached.stat().st_mtime, NOW.timestamp())

    def test_should_keep_the_tree_another_extraction_placed_meanwhile(self):
        # Arrange
        placed = self.cache / "shop" / "abc123"

        # Act
        tree = prepare_tree(
            ArchivingGitDouble("abc123", [README], placed_meanwhile=placed),
            FILESYSTEM_READ_TIME_KEEPER,
            self.create_request("v1"),
        )

        # Assert
        self.assertEqual(list(tree.root.iterdir()), [])

    def test_should_evict_the_trees_read_longest_ago_beyond_the_bound(self):
        # Arrange
        write_tree(self.cache / "tidepool" / "old999", 2048, LONG_AGO)
        (self.cache / ".removing").mkdir()

        # Act
        prepare_tree(ArchivingGitDouble("abc123", [README]), FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1"))

        # Assert
        self.assertEqual(list((self.cache / "tidepool").iterdir()), [])
        self.assertEqual(list((self.cache / "shop").iterdir()), [self.cache / "shop" / "abc123"])

    def test_should_stop_evicting_once_the_cache_is_back_within_its_bound(self):
        # Arrange
        write_tree(self.cache / "tidepool" / "old111", 2048, LONG_AGO)
        write_tree(self.cache / "tidepool" / "old222", 8, LAST_JUNE)

        # Act
        prepare_tree(ArchivingGitDouble("abc123", [README]), FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1"))

        # Assert
        self.assertEqual(list((self.cache / "tidepool").iterdir()), [self.cache / "tidepool" / "old222"])

    def test_should_refuse_a_ref_naming_no_commit(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_tree(ArchivingGitDouble("", [README]), FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1"))

        # Assert
        self.assertEqual(str(refusal.exception), "the ref v1 is not a commit of @PROJECT.shop")

    def test_should_refuse_an_archive_holding_a_member_outside_the_tree(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            prepare_tree(
                ArchivingGitDouble("abc123", [("../evil", b"x")]),
                FILESYSTEM_READ_TIME_KEEPER,
                self.create_request("v1"),
            )

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the archive of @PROJECT.shop holds ../evil, a member tarfile's data filter refuses",
        )


class PrepareTreeThatCannotWriteTest(PrepareTreeTestCase):
    def test_should_refuse_a_project_cache_whose_staging_path_runs_past_the_longest_path(self):
        # Arrange
        cache = create_path_of_length(self.root, LONGEST_PATH - len("/shop") - 7)

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            prepare_tree(
                ArchivingGitDouble("abc", [README]), FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1", cache=cache)
            )

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {cache}/shop/abc: File name too long")

    def test_should_refuse_an_archive_it_cannot_unpack(self):
        # Arrange
        file_under_a_file = ArchivingGitDouble("abc123", [("a", b"x"), ("a/b", b"y")])

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            prepare_tree(file_under_a_file, FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1"))

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.cache}/shop/abc123: Not a directory")

    def test_should_refuse_a_tree_place_a_file_holds(self):
        # Arrange
        (self.cache / "shop").mkdir(parents=True)
        (self.cache / "shop" / "abc123").write_text("not a tree")

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            prepare_tree(ArchivingGitDouble("abc123", [README]), FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1"))

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.cache}/shop/abc123: Not a directory")

    def test_should_refuse_a_stale_tree_whose_name_leaves_no_room_to_evict_it(self):
        # Arrange
        write_tree(self.cache / "tidepool" / NAME_LONGER_THAN_ITS_EVICTION_ALLOWS, 2048, LONG_AGO)

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            prepare_tree(ArchivingGitDouble("abc123", [README]), FILESYSTEM_READ_TIME_KEEPER, self.create_request("v1"))

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"cannot write {self.cache}/tidepool/{NAME_LONGER_THAN_ITS_EVICTION_ALLOWS}: File name too long",
        )

    def test_should_refuse_a_tree_whose_read_it_cannot_mark(self):
        # Arrange
        keeper = replace(FILESYSTEM_READ_TIME_KEEPER, stamp_read=refuse_to_stamp)

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            prepare_tree(ArchivingGitDouble("abc123", [README]), keeper, self.create_request("v1"))

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.cache}/shop/abc123: Operation not permitted")

    def test_should_refuse_a_cache_naming_the_path_it_cannot_read(self):
        # Arrange
        refusal_to_read = PermissionError(errno.EACCES, "Permission denied", "/srv/refs/shop/abc123")
        keeper = replace(FILESYSTEM_READ_TIME_KEEPER, read_stamp=create_refusing_stamp_reader(refusal_to_read))

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            prepare_tree(ArchivingGitDouble("abc123", [README]), keeper, self.create_request("v1"))

        # Assert
        self.assertEqual(str(refusal.exception), "cannot write /srv/refs/shop/abc123: Permission denied")

    def test_should_name_the_cache_when_the_refusal_to_read_it_names_no_path(self):
        # Arrange
        refusal_to_read = OSError(errno.EIO, "Input/output error")
        keeper = replace(FILESYSTEM_READ_TIME_KEEPER, read_stamp=create_refusing_stamp_reader(refusal_to_read))

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            prepare_tree(ArchivingGitDouble("abc123", [README]), keeper, self.create_request("v1"))

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.cache}: Input/output error")
