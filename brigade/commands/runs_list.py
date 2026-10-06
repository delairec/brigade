from brigade.runs.list_runs import list_runs

DOCUMENT_SCHEMA_VERSION = 1


def run(request, runtime) -> dict:
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "runs": list_runs(runtime.paths.state_root)}
