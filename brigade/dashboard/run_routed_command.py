import json
import sys
from dataclasses import dataclass

from brigade.dashboard.route_command import CommandRoute
from brigade.runtime import Runtime
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest

COMMAND_TIMEOUT_S = 120
OK = 200
NOT_FOUND = 404
SERVER_ERROR = 500


@dataclass(frozen=True)
class CommandAnswer:
    status: int
    document: str


def _run_brigade(arguments: tuple[str, ...], runtime: Runtime) -> ProcessRecord:
    return runtime.run_process(
        ProcessRequest(
            argv=(sys.executable, str(runtime.entry_point), *arguments),
            cwd=str(runtime.paths.home),
            timeout_s=COMMAND_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )


def _is_unknown(route: CommandRoute, runtime: Runtime) -> bool:
    if route.listing is None:
        return False
    listed = _run_brigade(route.listing.arguments, runtime)
    if listed.exit_code != 0:
        return False
    entries = json.loads(listed.stdout)[route.listing.collection]
    return route.identifier not in [entry[route.listing.field] for entry in entries]


def run_routed_command(route: CommandRoute, runtime: Runtime) -> CommandAnswer:
    record = _run_brigade(route.arguments, runtime)
    if record.exit_code == 0:
        return CommandAnswer(status=OK, document=record.stdout)
    status = NOT_FOUND if _is_unknown(route, runtime) else SERVER_ERROR
    return CommandAnswer(status=status, document=json.dumps({"error": record.stderr}))
