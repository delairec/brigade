import argparse
from pathlib import Path

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
FIELD_NAME_WIDTH = 6
TREE_FIELDS = ("ref", "sha", "kind", "root")


def _render_text(document: dict) -> str:
    lines = [
        f"@PROJECT.{document['project']}",
        *(f"{name:<{FIELD_NAME_WIDTH}}{document[name]}" for name in TREE_FIELDS if document[name] is not None),
    ]
    return "\n".join(lines)


def corpus(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    tree = prepare_project_tree(request, configuration, runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": tree.project,
        "ref": tree.ref,
        "sha": tree.sha,
        "kind": tree.kind,
        "root": str(tree.root),
    }


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
            required=True,
        ),
    ),
    run=corpus,
    render_text=_render_text,
)
