import argparse
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.corpus_reader import CorpusReader
from brigade.corpus.prepare_registered_tree import prepare_registered_tree
from brigade.corpus.prepare_tree import Tree
from brigade.corpus.read_entities import Entity
from brigade.corpus.tree_view_describer import TreeViewDescriber, locate_awawa_web
from brigade.corpus.view_request import ViewRequest
from brigade.errors import BrigadeError
from brigade.registry.find_project import find_project
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_FILES = "*.awawa"
NO_FILTER = ()


def _list_awawa_files(root: Path) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.stat().st_mtime_ns, path.stat().st_size)
            for path in root.rglob(AWAWA_FILES)
        )
    )


def _read_view_request(message: dict) -> ViewRequest:
    return ViewRequest(
        view=message.get("view"),
        entity_type=message.get("type"),
        field=message.get("field"),
        filters=tuple(message.get("filter", NO_FILTER)),
        search=message.get("search"),
        entity=message.get("entity"),
    )


class CorpusViewAnswerer:
    def __init__(
        self,
        projects: tuple[Entity, ...],
        configuration: Configuration,
        runtime: Runtime,
        run_awawa_process: Callable[[ProcessRequest], ProcessRecord],
    ):
        self.projects = projects
        self.configuration = configuration
        self.runtime = runtime
        self.run_awawa_process = run_awawa_process
        self.readings: dict[tuple[str, str | None], tuple[tuple, TreeViewDescriber]] = {}

    def answer(self, message: dict) -> dict:
        try:
            return {"document": self._describe(message)}
        except BrigadeError as error:
            return {"error": str(error)}

    def _describe(self, message: dict) -> dict:
        request = argparse.Namespace(project=message["project"], ref=message.get("ref"), worktree=None)
        project = find_project(self.projects, request.project)
        tree = prepare_registered_tree(project, request, self.configuration, self.runtime)
        return self._read(tree).describe(tree, _read_view_request(message))

    def _read(self, tree: Tree) -> TreeViewDescriber:
        key = (tree.project, tree.ref)
        stamp = (tree.sha, _list_awawa_files(tree.root))
        kept = self.readings.get(key)
        if kept is None or kept[0] != stamp:
            reader = CorpusReader(self.run_awawa_process, tree.root, self.configuration.ide_link)
            kept = (stamp, TreeViewDescriber(reader, locate_awawa_web(self.runtime.run_process)))
            self.readings[key] = kept
        return kept[1]
