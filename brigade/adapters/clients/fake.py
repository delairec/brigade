import json

from brigade.adapters.clients.describe_unreadable_output import describe_unreadable_output
from brigade.errors import BrigadeError

SCHEMA_VERSION = 1
CLIENT_NAME = "fake"


def _probe() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "client": CLIENT_NAME,
        "version_argv": None,
        "operations": ["probe", "launch", "result"],
        "features": [],
        "models": {},
    }


def _build_launch(request: dict) -> dict:
    recordings = request["settings"].get("recordings")
    if recordings is None:
        raise BrigadeError("the fake client adapter needs recordings in the table [clients.fake] of config.toml")
    return {
        "schema_version": SCHEMA_VERSION,
        "argv": ["cat", "--", f"{recordings}/{request['role']['name']}.json"],
        "environment": {},
        "stdin": None,
    }


def _replay_result(request: dict) -> dict:
    try:
        return json.loads(request["stdout"])
    except ValueError:
        return describe_unreadable_output(request["stderr"])


def answer(operation: str, request: dict) -> dict:
    if operation == "probe":
        return _probe()
    if operation == "launch-argv":
        return _build_launch(request)
    if operation == "parse-result":
        return _replay_result(request)
    raise BrigadeError(f"the fake client adapter does not answer {operation}")
