import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from brigade.errors import BrigadeError
from brigade.git.list_tracked_files import list_tracked_files
from brigade.git.read_main_branch import read_main_branch
from brigade.git.read_origin_url import read_origin_url
from brigade.registry.describe_remote import describe_remote
from brigade.system.run_process import ProcessRecord, ProcessRequest

CORPUS_FILES = "*.awawa"
REPOSITORY_ROOT = "."


@dataclass(frozen=True)
class ProjectDiscovery:
    path: Path
    remote: Optional[str]
    main: str
    corpus: Optional[str]
    forge: str


def _locate_corpus(files: tuple[str, ...]) -> Optional[str]:
    if not files:
        return None
    return posixpath.commonpath([posixpath.dirname(file) for file in files]) or REPOSITORY_ROOT


def discover_project(run_process: Callable[[ProcessRequest], ProcessRecord], path: Path) -> ProjectDiscovery:
    main = read_main_branch(run_process, path)
    if main is None:
        raise BrigadeError(f"{path} has neither an origin/HEAD nor a branch checked out; check out its main branch")
    remote = describe_remote(read_origin_url(run_process, path))
    return ProjectDiscovery(
        path=path,
        remote=remote.remote,
        main=main,
        corpus=_locate_corpus(list_tracked_files(run_process, path, CORPUS_FILES)),
        forge=remote.forge,
    )
