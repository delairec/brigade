import shlex

from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1


def install(request: dict, runtime: Runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "scheduler": "loop",
        "unit_files": [],
        "cron_line": None,
        "keep_running": f"{shlex.quote(request['brigade'])} tick --loop",
    }
