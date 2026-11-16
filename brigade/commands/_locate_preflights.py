import functools
from collections.abc import Callable
from pathlib import Path

from brigade.preflights.preflight_places import MACHINE_PREFLIGHTS_DIRECTORY, PROJECT_PREFLIGHTS_DIRECTORY
from brigade.preflights.read_preflight_entity import read_preflight_entity
from brigade.preflights.read_preflight_file import read_preflight_file
from brigade.preflights.run_preflight import BUILT_IN_PREFLIGHTS
from brigade.registry.find_project_at import find_project_at
from brigade.registry.locate_project_corpus import locate_project_corpus
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime


def _locate_project_preflights(project: Path, runtime: Runtime) -> Callable[[str], dict | None]:
    corpus = locate_project_corpus(find_project_at(read_projects(runtime), project))
    if corpus is None:
        return functools.partial(read_preflight_file, project / PROJECT_PREFLIGHTS_DIRECTORY)
    return functools.partial(read_preflight_entity, runtime.run_process, project / corpus)


def locate_preflights(project: Path, runtime: Runtime) -> tuple[Callable[[str], dict | None], ...]:
    return (
        _locate_project_preflights(project, runtime),
        functools.partial(read_preflight_file, runtime.paths.config_root / MACHINE_PREFLIGHTS_DIRECTORY),
        functools.partial(read_preflight_file, BUILT_IN_PREFLIGHTS),
    )
