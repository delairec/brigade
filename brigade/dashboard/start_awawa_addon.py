import contextlib
import functools
import sys
from collections.abc import Iterator
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.corpus.read_entities import Entity
from brigade.dashboard.awawa_addon_supervisor import AwawaAddonSupervisor
from brigade.errors import BrigadeError
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.start_piped_process import PipedProcessRequest

ADDON_COMMAND = "awawa-addon"
ANSWER_TIMEOUT_S = 120.0
PATH_FIELD = "PATH"
NO_HOLDER = frozenset()


def _holds_a_corpus(project: Entity, runtime: Runtime) -> bool:
    status = read_awawa_document(runtime.run_process, Path(read_project_field(project, PATH_FIELD)), ("status",))
    return status["summary"]["files"] > 0


def _list_corpus_holders(runtime: Runtime) -> frozenset[str]:
    try:
        require_operational_corpus(runtime.paths)
        return frozenset(project.name for project in read_projects(runtime) if _holds_a_corpus(project, runtime))
    except BrigadeError:
        return NO_HOLDER


@contextlib.contextmanager
def start_awawa_addon(runtime: Runtime) -> Iterator[AwawaAddonSupervisor]:
    request = PipedProcessRequest(
        argv=(sys.executable, str(runtime.entry_point), ADDON_COMMAND), cwd=str(runtime.paths.home)
    )
    addon = AwawaAddonSupervisor(
        _list_corpus_holders(runtime), functools.partial(runtime.start_piped_process, request), ANSWER_TIMEOUT_S
    )
    addon.open()
    try:
        yield addon
    finally:
        addon.stop()
