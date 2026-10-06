import os
import shutil
import stat
import tarfile
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from brigade.errors import BrigadeError
from brigade.git.archive_commit import archive_commit
from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.git.resolve_commit import resolve_commit
from brigade.system.hold_lock import hold_lock
from brigade.system.run_process import ProcessRecord, ProcessRequest

WORKTREE_PREFIX = "worktree:"
HIDDEN_PREFIX = "."
ARCHIVE_NAME = "commit.tar"
STAGED_TREE_NAME = "tree"
ARCHIVE_KIND = "archive"
WORKTREE_KIND = "worktree"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
NANOSECONDS_PER_MICROSECOND = 1000
NOTHING_MEASURED = 0
TRUSTED_EXTRACTION = {"filter": "fully_trusted"} if hasattr(tarfile, "fully_trusted_filter") else {}


@dataclass(frozen=True)
class TreeRequest:
    project: str
    repository: Path
    ref: Optional[str]
    worktree: Optional[Path]
    cache: Path
    cache_bound_bytes: int
    cache_lock: Path
    now: datetime


@dataclass(frozen=True)
class Tree:
    project: str
    ref: Optional[str]
    sha: str
    kind: str
    root: Path


@dataclass(frozen=True)
class _CachedTree:
    path: Path
    last_read_ns: int
    size_bytes: int


def _find_worktree(
    run_process: Callable[[ProcessRequest], ProcessRecord], request: TreeRequest
) -> Worktree:
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


def _stage_tree(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, sha: str, staging: Path
) -> Path:
    archive = staging / ARCHIVE_NAME
    staged_tree = staging / STAGED_TREE_NAME
    archive_commit(run_process, repository, sha, archive)
    with tarfile.open(archive) as commit_tar:
        commit_tar.extractall(staged_tree, **TRUSTED_EXTRACTION)
    return staged_tree


def _place_tree(staged_tree: Path, root: Path) -> None:
    if not root.is_dir():
        os.rename(staged_tree, root)


def _mark_read(root: Path, now: datetime) -> None:
    read_ns = (now - EPOCH) // timedelta(microseconds=1) * NANOSECONDS_PER_MICROSECOND
    os.utime(root, ns=(read_ns, read_ns))


def _measure_file(path: str) -> int:
    status = os.lstat(path)
    return status.st_size if stat.S_ISREG(status.st_mode) else NOTHING_MEASURED


def _measure_tree(root: Path) -> int:
    return sum(
        _measure_file(os.path.join(directory, name)) for directory, _, names in os.walk(root) for name in names
    )


def _list_visible_directories(parent: Path) -> list[Path]:
    return [entry for entry in parent.iterdir() if not entry.name.startswith(HIDDEN_PREFIX) and entry.is_dir()]


def _list_cached_trees(cache: Path) -> list[_CachedTree]:
    return [
        _CachedTree(path=tree, last_read_ns=tree.stat().st_mtime_ns, size_bytes=_measure_tree(tree))
        for project in _list_visible_directories(cache)
        for tree in _list_visible_directories(project)
    ]


def _remove_tree(root: Path) -> None:
    doomed = root.parent / f"{HIDDEN_PREFIX}{root.name}.{uuid.uuid4().hex}"
    os.rename(root, doomed)
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
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=HIDDEN_PREFIX, dir=root.parent))
    try:
        staged_tree = _stage_tree(run_process, request.repository, sha, staging)
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
