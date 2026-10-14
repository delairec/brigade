import os
import shutil
import stat
import tarfile
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from brigade.errors import BrigadeError, CannotWrite
from brigade.git.archive_commit import archive_commit
from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.git.resolve_commit import resolve_commit
from brigade.system.create_directory import create_directory
from brigade.system.hold_lock import hold_lock
from brigade.system.run_process import ProcessRecord, ProcessRequest

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


def _create_staging(root: Path) -> Path:
    try:
        return Path(tempfile.mkdtemp(prefix=HIDDEN_PREFIX, dir=root.parent))
    except OSError as error:
        raise CannotWrite(root, error) from error


def _unpack(archive: Path, staged_tree: Path, root: Path) -> None:
    with tarfile.open(archive) as commit_tar:
        try:
            commit_tar.extractall(staged_tree, filter="data")
        except OSError as error:
            raise CannotWrite(root, error) from error


def _stage_tree(
    run_process: Callable[[ProcessRequest], ProcessRecord], request: TreeRequest, sha: str, staging: Path, root: Path
) -> Path:
    archive = staging / ARCHIVE_NAME
    staged_tree = staging / STAGED_TREE_NAME
    archive_commit(run_process, request.repository, sha, archive)
    try:
        _unpack(archive, staged_tree, root)
    except tarfile.FilterError as error:
        raise BrigadeError(
            f"the archive of @PROJECT.{request.project} holds {error.tarinfo.name}, a member tarfile's data filter"
            " refuses"
        ) from error
    return staged_tree


def _place_tree(staged_tree: Path, root: Path) -> None:
    if root.is_dir():
        return
    try:
        staged_tree.rename(root)
    except OSError as error:
        raise CannotWrite(root, error) from error


def _mark_read(root: Path, now: datetime) -> None:
    read_ns = (now - EPOCH) // timedelta(microseconds=1) * NANOSECONDS_PER_MICROSECOND
    try:
        os.utime(root, ns=(read_ns, read_ns))
    except OSError as error:
        raise CannotWrite(root, error) from error


def _measure_file(path: Path) -> int:
    status = path.lstat()
    return status.st_size if stat.S_ISREG(status.st_mode) else NOTHING_MEASURED


def _measure_tree(root: Path) -> int:
    return sum(_measure_file(Path(directory) / name) for directory, _, names in os.walk(root) for name in names)


def _list_visible_directories(parent: Path) -> list[Path]:
    return [entry for entry in parent.iterdir() if not entry.name.startswith(HIDDEN_PREFIX) and entry.is_dir()]


def _list_cached_trees(cache: Path) -> list[_CachedTree]:
    try:
        return [
            _CachedTree(path=tree, last_read_ns=tree.stat().st_mtime_ns, size_bytes=_measure_tree(tree))
            for project in _list_visible_directories(cache)
            for tree in _list_visible_directories(project)
        ]
    except OSError as error:
        raise CannotWrite(error.filename or cache, error) from error


def _remove_tree(root: Path) -> None:
    doomed = root.parent / f"{HIDDEN_PREFIX}{root.name}.{uuid.uuid4().hex}"
    try:
        root.rename(doomed)
    except OSError as error:
        raise CannotWrite(root, error) from error
    shutil.rmtree(doomed, ignore_errors=True)


def _prune(cache: Path, bound_bytes: int, kept: Path) -> None:
    cached_trees = _list_cached_trees(cache)
    total_bytes = sum(tree.size_bytes for tree in cached_trees)
    removable = sorted((tree for tree in cached_trees if tree.path != kept), key=lambda tree: tree.last_read_ns)
    for tree in removable:
        if total_bytes <= bound_bytes:
            return
        _remove_tree(tree.path)
        total_bytes -= tree.size_bytes


def _extract_tree(
    run_process: Callable[[ProcessRequest], ProcessRecord], request: TreeRequest, sha: str, root: Path
) -> None:
    create_directory(root.parent)
    staging = _create_staging(root)
    try:
        staged_tree = _stage_tree(run_process, request, sha, staging, root)
        with hold_lock(request.cache_lock):
            _place_tree(staged_tree, root)
            _mark_read(root, request.now)
            _prune(request.cache, request.cache_bound_bytes, root)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _reuse_cached_tree(root: Path, request: TreeRequest) -> bool:
    with hold_lock(request.cache_lock):
        if not root.is_dir():
            return False
        _mark_read(root, request.now)
        return True


def _read_archive(run_process: Callable[[ProcessRequest], ProcessRecord], request: TreeRequest) -> Tree:
    sha = resolve_commit(run_process, request.repository, request.ref)
    if sha is None:
        raise BrigadeError(f"the ref {request.ref} is not a commit of @PROJECT.{request.project}")
    root = request.cache / request.project / sha
    if not _reuse_cached_tree(root, request):
        _extract_tree(run_process, request, sha, root)
    return Tree(project=request.project, ref=request.ref, sha=sha, kind=ARCHIVE_KIND, root=root)


def prepare_tree(run_process: Callable[[ProcessRequest], ProcessRecord], request: TreeRequest) -> Tree:
    if request.worktree is not None or request.ref.startswith(WORKTREE_PREFIX):
        return _read_worktree(run_process, request)
    return _read_archive(run_process, request)
