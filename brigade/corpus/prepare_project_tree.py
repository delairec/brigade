import argparse
from pathlib import Path

from brigade.corpus.prepare_tree import FILESYSTEM_READ_TIME_KEEPER, Tree, TreeRequest, prepare_tree
from brigade.corpus.read_entities import Entity
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration

REPOSITORY_FIELD = "PATH"
MAIN_FIELD = "MAIN"
REFS_CACHE_DIRECTORY = "refs"
BYTES_PER_MB = 1024 * 1024
CACHE_LOCK_FILE = "refs-cache.lock"


def _choose_ref(request: argparse.Namespace, project: Entity) -> str | None:
    if request.ref is not None:
        return request.ref
    if request.worktree is not None:
        return None
    return read_project_field(project, MAIN_FIELD)


def prepare_project_tree(request: argparse.Namespace, configuration: Configuration, runtime: Runtime) -> Tree:
    require_operational_corpus(runtime.paths)
    project = find_project(read_projects(runtime), request.project)
    repository = next(field.value for field in project.fields if field.name == REPOSITORY_FIELD)
    worktree = request.worktree.absolute() if request.worktree is not None else None
    return prepare_tree(
        runtime.run_process,
        FILESYSTEM_READ_TIME_KEEPER,
        TreeRequest(
            project=project.name,
            repository=Path(repository),
            ref=_choose_ref(request, project),
            worktree=worktree,
            cache=runtime.paths.cache_root / REFS_CACHE_DIRECTORY,
            cache_bound_bytes=configuration.refs_cache_mb * BYTES_PER_MB,
            cache_lock=runtime.paths.lock_directory / CACHE_LOCK_FILE,
            now=runtime.now,
        ),
    )
