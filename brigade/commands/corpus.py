import argparse
import json
from pathlib import Path

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.corpus.corpus_reader import CorpusReader
from brigade.corpus.describe_corpus_view import CorpusView, describe_corpus_view
from brigade.corpus.describe_view_document import ViewRequest, describe_view_document
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_corpus_types import read_corpus_types
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.find_awawa_web import find_awawa_web
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
FIELD_NAME_WIDTH = 6
TREE_FIELDS = ("ref", "sha", "kind", "root")
AWAWA_WEB_ADDRESS = "http://127.0.0.1:7878/"
NOTHING = "nothing"
VIEWS = ("tree", "board", "dependencies", "health")
JSON_INDENT = 2


def _render_board(document: dict) -> list[str]:
    field = document["field"]
    return [
        f"{field} {column['value']}: {', '.join(column['targets'])}"
        if column["value"] is not None
        else f"no {field}: {', '.join(column['targets'])}"
        for column in document["board"]
    ]


def _render_dependencies(dependencies: dict) -> list[str]:
    reached = ", ".join(entity["target"] for entity in dependencies["reaches"]) or NOTHING
    referencing = ", ".join(dependencies["referenced_by"]) or NOTHING
    return [
        f"{dependencies['entity']} reaches {reached}",
        f"{dependencies['entity']} is referenced by {referencing}",
    ]


def _render_text(document: dict) -> str:
    if "view" in document:
        return json.dumps(document, indent=JSON_INDENT)
    lines = [
        f"@PROJECT.{document['project']}",
        *(f"{name:<{FIELD_NAME_WIDTH}}{document[name]}" for name in TREE_FIELDS if document[name] is not None),
        *(
            f"{entity['target']}  {entity['status']}  {entity['file']}:{entity['line']}"
            for entity in document.get("entities", ())
        ),
        *(_render_board(document) if "board" in document else ()),
        *(_render_dependencies(document["dependencies"]) if "dependencies" in document else ()),
    ]
    return "\n".join(lines)


def corpus(request: argparse.Namespace, runtime: Runtime) -> dict:
    if request.view is None and request.type is None and (request.field is not None or request.entity is not None):
        raise BrigadeError("--field and --entity read the entities of --type")
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    tree = prepare_project_tree(request, configuration, runtime)
    document = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": tree.project,
        "ref": tree.ref,
        "sha": tree.sha,
        "kind": tree.kind,
        "root": str(tree.root),
        "types": read_corpus_types(runtime.run_process, tree.root),
    }
    if request.view is None and request.type is None:
        return document
    awawa_web = {"awawa_web": AWAWA_WEB_ADDRESS if find_awawa_web(runtime.run_process) else None}
    if request.view is not None:
        reader = CorpusReader(runtime.run_process, tree.root, configuration.ide_link)
        view_request = ViewRequest(
            view=request.view,
            entity_type=request.type,
            field=request.field,
            filters=tuple(request.filter),
            search=request.search,
            entity=request.entity,
        )
        return document | awawa_web | describe_view_document(reader, view_request)
    view = CorpusView(
        entity_type=request.type, field=request.field, entity=request.entity, ide_link=configuration.ide_link
    )
    return document | describe_corpus_view(runtime.run_process, tree.root, view) | awawa_web


COMMAND = Command(
    path=("corpus",),
    help="read a registered project's tree at a branch, a SHA or a worktree; -- <awawa args> runs awawa there",
    arguments=(
        Argument(("project",)),
        ExclusiveArguments(
            (
                Argument(
                    ("--ref",),
                    {
                        "help": "a branch or a SHA, extracted to the cache;"
                        " worktree:<branch> reads the worktree of that branch;"
                        " the MAIN branch of the project by default"
                    },
                ),
                Argument(
                    ("--worktree",), {"type": Path, "help": "the path of a worktree of the project, read in place"}
                ),
            ),
        ),
        Argument(("--type",), {"help": "the entity type whose entities the document lists"}),
        Argument(("--field",), {"help": "with --type, the field whose values the board groups the entities by"}),
        Argument(
            ("--entity",),
            {
                "help": "with --type, an @TYPE.Name whose dependencies the document lists;"
                " with --view, the detail of that entity added to the view"
            },
        ),
        Argument(
            ("--view",),
            {"choices": VIEWS, "help": "the document of one view of the corpus, by the rules of awawa-ui"},
        ),
        Argument(
            ("--filter",),
            {
                "action": "append",
                "default": [],
                "metavar": "<field>=<value>",
                "help": "with --view, keeps the entities of --type whose field holds the value;"
                " <field>.<field>=<value> reads a field of the entities it refers to; repeatable",
            },
        ),
        Argument(
            ("--search",),
            {"help": "with --view, keeps the entities whose label, code, facts, status or file carries the text"},
        ),
    ),
    run=corpus,
    render_text=_render_text,
)
