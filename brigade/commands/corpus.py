import argparse
from pathlib import Path

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.corpus.describe_corpus_view import CorpusView, describe_corpus_view
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.find_awawa_web import find_awawa_web
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
FIELD_NAME_WIDTH = 6
TREE_FIELDS = ("ref", "sha", "kind", "root")
AWAWA_WEB_ADDRESS = "http://127.0.0.1:7878/"
NOTHING = "nothing"


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
    if request.type is None and (request.field is not None or request.entity is not None):
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
    }
    view = CorpusView(
        entity_type=request.type, field=request.field, entity=request.entity, ide_link=configuration.ide_link
    )
    reading = document | describe_corpus_view(runtime.run_process, tree.root, view)
    if request.type is None:
        return reading
    awawa_web = AWAWA_WEB_ADDRESS if find_awawa_web(runtime.run_process) else None
    return reading | {"awawa_web": awawa_web}


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
                        " worktree:<branch> reads the worktree of that branch"
                    },
                ),
                Argument(
                    ("--worktree",), {"type": Path, "help": "the path of a worktree of the project, read in place"}
                ),
            ),
        ),
        Argument(("--type",), {"help": "the entity type whose entities the document lists"}),
        Argument(("--field",), {"help": "with --type, the field whose values the board groups the entities by"}),
        Argument(("--entity",), {"help": "with --type, an @TYPE.Name whose dependencies the document lists"}),
    ),
    run=corpus,
    render_text=_render_text,
)
