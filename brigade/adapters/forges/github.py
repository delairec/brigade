import json

from brigade.runtime import Runtime
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest

HOST = "github.com"
PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0
DOCUMENT_SCHEMA_VERSION = 1


def _read_active_login(hosts_document: str):
    try:
        accounts = json.loads(hosts_document)["hosts"][HOST]
    except (ValueError, KeyError, TypeError):
        return None
    return next((account.get("login") for account in accounts if account.get("active")), None)


def describe_account(request: dict, runtime: Runtime) -> dict:
    record = runtime.run_process(
        ProcessRequest(
            argv=("gh", "auth", "status", "--active", "--hostname", HOST, "--json", "hosts"),
            cwd=PROBE_DIRECTORY,
            timeout_s=PROBE_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    login = _read_active_login(record.stdout) if record.exit_code == 0 else None
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "login": login}
