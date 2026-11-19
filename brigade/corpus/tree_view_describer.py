from collections.abc import Callable

from brigade.corpus.corpus_reader import CorpusReader
from brigade.corpus.describe_view_document import describe_view_document
from brigade.corpus.prepare_tree import Tree
from brigade.corpus.view_request import ViewRequest
from brigade.system.find_awawa_web import find_awawa_web
from brigade.system.run_process import ProcessRecord, ProcessRequest

DOCUMENT_SCHEMA_VERSION = 1
AWAWA_WEB_ADDRESS = "http://127.0.0.1:7878/"


def locate_awawa_web(run_process: Callable[[ProcessRequest], ProcessRecord]) -> str | None:
    return AWAWA_WEB_ADDRESS if find_awawa_web(run_process) else None


class TreeViewDescriber:
    def __init__(self, reader: CorpusReader, awawa_web: str | None):
        self.reader = reader
        self.awawa_web = awawa_web

    def describe(self, tree: Tree, request: ViewRequest, refs: list[str]) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "project": tree.project,
            "ref": tree.ref,
            "sha": tree.sha,
            "refs": refs,
            "kind": tree.kind,
            "root": str(tree.root),
            "types": [row["type"] for row in self.reader.status["types"]],
            "awawa_web": self.awawa_web,
        } | describe_view_document(self.reader, request)
