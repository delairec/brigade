from brigade.commands.prepare_project_tree import prepare_project_tree

DOCUMENT_SCHEMA_VERSION = 1


def run(request, runtime) -> dict:
    tree = prepare_project_tree(request, runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": tree.project,
        "ref": tree.ref,
        "sha": tree.sha,
        "kind": tree.kind,
        "root": str(tree.root),
    }
