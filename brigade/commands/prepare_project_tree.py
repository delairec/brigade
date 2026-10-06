from pathlib import Path

from brigade.corpus.prepare_tree import Tree, TreeRequest, prepare_tree
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.system.read_optional_configuration import read_optional_configuration

REPOSITORY_FIELD = "PATH"
CONFIGURATION_FILE = "config.toml"
REFS_CACHE_DIRECTORY = "refs"
BYTES_PER_MB = 1024 * 1024


def prepare_project_tree(request, runtime) -> Tree:
    require_operational_corpus(runtime.paths.config_root)
    project = find_project(read_projects(runtime), request.project)
    repository = next(field.value for field in project.fields if field.name == REPOSITORY_FIELD)
    configuration = read_optional_configuration(runtime.paths.config_root / CONFIGURATION_FILE)
    worktree = request.worktree.absolute() if request.worktree is not None else None
    return prepare_tree(
        runtime.run_process,
        TreeRequest(
            project=project.name,
            repository=Path(repository),
            ref=request.ref,
            worktree=worktree,
            cache=runtime.paths.cache_root / REFS_CACHE_DIRECTORY,
            cache_bound_bytes=configuration.refs_cache_mb * BYTES_PER_MB,
            now=runtime.now,
        ),
    )
