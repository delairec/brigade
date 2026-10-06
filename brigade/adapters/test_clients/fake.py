import json

from brigade.adapters.clients.describe_unreadable_output import describe_unreadable_output
from brigade.errors import BrigadeError

SCHEMA_VERSION = 1
CLIENT_NAME = "fake"
FEATURE_SEPARATOR = ","
SLOW_CLIENT_SCRIPT = 'sleep "$1"; if [ -n "$2" ]; then printf "%s\\n" "$2" >> "$BRIGADE_PROGRESS_FILE"; fi; cat -- "$3"'
NO_DELAY = "0"
NO_PROGRESS = ""


def _read_features(request: dict) -> list[str]:
    declared = request.get("settings", {}).get("features", "")
    return [feature.strip() for feature in declared.split(FEATURE_SEPARATOR) if feature.strip()]


def _probe(request: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "client": CLIENT_NAME,
        "version_argv": None,
        "operations": ["probe", "launch", "result"],
        "features": _read_features(request),
        "models": {},
    }


def _build_argv(settings: dict, recording: str) -> list[str]:
    delay = settings.get("delay")
    progress = settings.get("progress")
    if delay is None and progress is None:
        return ["cat", "--", recording]
    return ["sh", "-c", SLOW_CLIENT_SCRIPT, CLIENT_NAME, delay or NO_DELAY, progress or NO_PROGRESS, recording]


def _build_launch(request: dict) -> dict:
    recordings = request["settings"].get("recordings")
    if recordings is None:
        raise BrigadeError("the fake client adapter needs recordings in the table [clients.fake] of config.toml")
    return {
        "schema_version": SCHEMA_VERSION,
        "argv": _build_argv(request["settings"], f"{recordings}/{request['role']['name']}.json"),
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
        return _probe(request)
    if operation == "launch-argv":
        return _build_launch(request)
    if operation == "parse-result":
        return _replay_result(request)
    raise BrigadeError(f"the fake client adapter does not answer {operation}")
