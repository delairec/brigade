from brigade.runs.read_run_logs import read_run_logs

DOCUMENT_SCHEMA_VERSION = 1


def run(request, runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": request.run,
        "lines": read_run_logs(runtime.paths.state_root, request.run, request.tail),
    }
