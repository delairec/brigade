import os
import stat
import tarfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.git.archive_commit import archive_commit
from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.git.resolve_commit import resolve_commit
from brigade.system.create_directory import create_directory
from brigade.system.hold_lock import hold_lock
from brigade.system.place_directory_atomically import place_directory_atomically
from brigade.system.refuse_failed_write import refuse_failed_write
from brigade.system.remove_directory import remove_directory
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.system.stage_directory import stage_directory

WORKTREE_PREFIX = "worktree:"
HIDDEN_PREFIX = "."
ARCHIVE_NAME = "commit.tar"
STAGED_TREE_NAME = "tree"
ARCHIVE_KIND = "archive"
WORKTREE_KIND = "worktree"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
NANOSECONDS_PER_MICROSECOND = 1000
NOTHING_MEASURED = 0


@dataclass(frozen=True)
class TreeRequest:
    project: str
    repository: Path
    ref: str | None
    worktree: Path | None
    cache: Path
    cache_bound_bytes: int
    cache_lock: Path
    now: datetime


@dataclass(frozen=True)
class Tree:
    project: str
    ref: str | None
    sha: str
    kind: str
    root: Path


@dataclass(frozen=True)
class ReadTimeKeeper:
    stamp_read: Callable[[Path, int], None]
    read_stamp: Callable[[Path], int]


def _stamp_read(tree: Path, read_ns: int) -> None:
    os.utime(tree, ns=(read_ns, read_ns))


def _read_stamp(tree: Path) -> int:
    return tree.stat().st_mtime_ns


FILESYSTEM_READ_TIME_KEEPER = ReadTimeKeeper(stamp_read=_stamp_read, read_stamp=_read_stamp)


@dataclass(frozen=True)
class _CachedTree:
    path: Path
    last_read_ns: int
    size_bytes: int


def _find_worktree(run_process: Callable[[ProcessRequest], ProcessRecord], request: TreeRequest) -> Worktree:
    worktrees = list_worktrees(run_process, request.repository)
    if request.worktree is not None:
        wanted_path = request.worktree.resolve()
        found = next((worktree for worktree in worktrees if worktree.path.resolve() == wanted_path), None)
        if found is None:
            raise BrigadeError(f"no worktree of @PROJECT.{request.project} is at {request.worktree}")
        return found
    branch = request.ref[len(WORKTREE_PREFIX) :]
    found = next((worktree for worktree in worktrees if worktree.branch == branch), None)
    if found is None:
        raise BrigadeError(f"no worktree of @PROJECT.{request.project} has the branch {branch} checked out")
    return found


def _read_worktree(run_process: Callable[[ProcessRequest], ProcessRecord], request: TreeRequest) -> Tree:
    worktree = _find_worktree(run_process, request)
    return Tree(project=request.project, ref=request.ref, sha=worktree.head, kind=WORKTREE_KIND, root=worktree.path)


def _unpack(archive: Path, staged_tree: Path) -> None:
    with tarfile.open(archive) as commit_tar:
        commit_tar.extractall(staged_tree, filter="data")


def _stage_tree(
    run_process: Callable[[ProcessRequest], ProcessRecord], request: TreeRequest, sha: str, staging: Path
) -> Path:
    archive = staging / ARCHIVE_NAME
    staged_tree = staging / STAGED_TREE_NAME
    archive_commit(run_process, request.repository, sha, archive)
    try:
        _unpack(archive, staged_tree)
    except tarfile.FilterError as error:
        raise BrigadeError(
            f"the archive of @PROJECT.{request.project} holds {error.tarinfo.name}, a member tarfile's data filter"
            " refuses"
        ) from error
    return staged_tree


def _mark_read(root: Path, now: datetime, keeper: ReadTimeKeeper) -> None:
    read_ns = (now - EPOCH) // timedelta(microseconds=1) * NANOSECONDS_PER_MICROSECOND
    with refuse_failed_write(root):
        keeper.stamp_read(root, read_ns)


def _measure_file(path: Path) -> int:
    status = path.lstat()
    return status.st_size if stat.S_ISREG(status.st_mode) else NOTHING_MEASURED


def _measure_tree(root: Path) -> int:
    return sum(_measure_file(Path(directory) / name) for directory, _, names in os.walk(root) for name in names)


def _list_visible_directories(parent: Path) -> list[Path]:
    return [entry for entry in parent.iterdir() if not entry.name.startswith(HIDDEN_PREFIX) and entry.is_dir()]


def _list_cached_trees(cache: Path, keeper: ReadTimeKeeper) -> list[_CachedTree]:
    with refuse_failed_write(cache):
        return [
            _CachedTree(path=tree, last_read_ns=keeper.read_stamp(tree), size_bytes=_measure_tree(tree))
            for project in _list_visible_directories(cache)
            for tree in _list_visible_directories(project)
        ]


def _prune(cache: Path, bound_bytes: int, kept: Path, keeper: ReadTimeKeeper) -> None:
    cached_trees = _list_cached_trees(cache, keeper)
    total_bytes = sum(tree.size_bytes for tree in cached_trees)
    removable = sorted((tree for tree in cached_trees if tree.path != kept), key=lambda tree: tree.last_read_ns)
    for tree in removable:
        if total_bytes <= bound_bytes:
            return
        remove_directory(tree.path)
        total_bytes -= tree.size_bytes


def _extract_tree(
    run_process: Callable[[ProcessRequest], ProcessRecord],
    keeper: ReadTimeKeeper,
    request: TreeRequest,
    sha: str,
    root: Path,
) -> None:
    create_directory(root.parent)
    with stage_directory(root) as staging:
        staged_tree = _stage_tree(run_process, request, sha, staging)
        with hold_lock(request.cache_lock):
            place_directory_atomically(staged_tree, root)
            _mark_read(root, request.now, keeper)
            _prune(request.cache, request.cache_bound_bytes, root, keeper)


def _reuse_cached_tree(root: Path, request: TreeRequest, keeper: ReadTimeKeeper) -> bool:
    with hold_lock(request.cache_lock):
        if not root.is_dir():
            return False
        _mark_read(root, request.now, keeper)
        return True


def _read_archive(
    run_process: Callable[[ProcessRequest], ProcessRecord], keeper: ReadTimeKeeper, request: TreeRequest
) -> Tree:
    sha = resolve_commit(run_process, request.repository, request.ref)
    if sha is None:
        raise BrigadeError(f"the ref {request.ref} is not a commit of @PROJECT.{request.project}")
    root = request.cache / request.project / sha
    if not _reuse_cached_tree(root, request, keeper):
        _extract_tree(run_process, keeper, request, sha, root)
    return Tree(project=request.project, ref=request.ref, sha=sha, kind=ARCHIVE_KIND, root=root)


def prepare_tree(
    run_process: Callable[[ProcessRequest], ProcessRecord], keeper: ReadTimeKeeper, request: TreeRequest
) -> Tree:
    if request.worktree is not None or request.ref.startswith(WORKTREE_PREFIX):
        return _read_worktree(run_process, request)
    return _read_archive(run_process, keeper, request)
