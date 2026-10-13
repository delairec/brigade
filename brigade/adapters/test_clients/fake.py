import json
from datetime import UTC, datetime
from pathlib import Path

from brigade.adapters.clients.describe_unreadable_output import describe_unreadable_output
from brigade.adapters.documents import awawa, markdown
from brigade.errors import BrigadeError
from brigade.system.name_document_plugin import name_document_plugin

SCHEMA_VERSION = 1
CLIENT_NAME = "fake"
SETTING_SEPARATOR = ","
REPLAYED_OPERATIONS = ["probe", "launch", "result"]
SLOW_CLIENT_SCRIPT = (
    'sleep "$1"; until [ "$(date -u +%s)" -ge "$5" ]; do sleep 0.1; done;'
    ' if [ -n "$2" ]; then printf "%s\\n" "$2" >> "$BRIGADE_PROGRESS_FILE"; fi;'
    ' while IFS= read -r line || [ -n "$line" ]; do printf "%s\\n" "$line"; sleep "$4"; done < "$3"'
)
NO_DELAY = "0"
NO_PROGRESS = ""
NO_INTERVAL = "0"
NO_SOFT_LIMIT = "0"
GRACEFUL_STOP = "graceful_stop"
STOP_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
SLOW_CLIENT_SETTINGS = ("delay", "progress", "interval")
TRANSCRIPTS_RECORDING_SUFFIX = ".transcripts.json"
RESUMED_RECORDING_SUFFIX = ".resumed.json"
DOCUMENT_PLUGINS = {"markdown": markdown, "awawa": awawa}
NO_RUNTIME_NEEDED = None


def _read_list_setting(request: dict, name: str) -> list[str]:
    declared = request.get("settings", {}).get(name, "")
    return [value.strip() for value in declared.split(SETTING_SEPARATOR) if value.strip()]


def _probe(request: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "client": CLIENT_NAME,
        "version_argv": None,
        "operations": [*REPLAYED_OPERATIONS, *_read_list_setting(request, "operations")],
        "features": _read_list_setting(request, "features"),
        "models": {},
    }


def _read_soft_limit(request: dict):
    if request["stop_at"] is None or GRACEFUL_STOP not in _read_list_setting(request, "features"):
        return None
    return str(round(datetime.strptime(request["stop_at"], STOP_AT_FORMAT).replace(tzinfo=UTC).timestamp()))


def _build_argv(settings: dict, recording: str, soft_limit) -> list[str]:
    if soft_limit is None and not any(name in settings for name in SLOW_CLIENT_SETTINGS):
        return ["cat", "--", recording]
    return [
        "sh",
        "-c",
        SLOW_CLIENT_SCRIPT,
        CLIENT_NAME,
        settings.get("delay", NO_DELAY),
        settings.get("progress", NO_PROGRESS),
        recording,
        settings.get("interval", NO_INTERVAL),
        soft_limit or NO_SOFT_LIMIT,
    ]


def _holds_entry(progress_file: Path) -> bool:
    plugin = DOCUMENT_PLUGINS[name_document_plugin(progress_file)]
    return plugin.detect_entry({"path": str(progress_file)}, NO_RUNTIME_NEEDED)["holds_entry"]


def _choose_recording(recordings: str, request: dict) -> str:
    role = request["role"]["name"]
    resumed = Path(recordings) / f"{role}{RESUMED_RECORDING_SUFFIX}"
    if resumed.exists() and _holds_entry(Path(request["progress_file"])):
        return str(resumed)
    return f"{recordings}/{role}.json"


def _build_launch(request: dict) -> dict:
    recordings = request["settings"].get("recordings")
    if recordings is None:
        raise BrigadeError("the fake client adapter needs recordings in the table [clients.fake] of config.toml")
    return {
        "schema_version": SCHEMA_VERSION,
        "argv": _build_argv(request["settings"], _choose_recording(recordings, request), _read_soft_limit(request)),
        "environment": {},
        "stdin": None,
        "session_id": request["session_id"],
    }


def _read_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.strip()]


def _replay_result(request: dict) -> dict:
    try:
        return json.loads(request["stdout"].strip().rpartition("\n")[2])
    except ValueError:
        return describe_unreadable_output(request["stderr"])


def _read_line_action(line: str) -> dict:
    try:
        document = json.loads(line)
    except ValueError:
        return {"kind": "text", "summary": line}
    return {"kind": "result", "summary": document["outcome"]}


def _read_actions(request: dict) -> dict:
    actions = [_read_line_action(line) for line in _read_lines(request["output"])]
    return {"schema_version": SCHEMA_VERSION, "actions": actions}


def _replay_transcripts(request: dict) -> dict:
    recording = Path(request["settings"]["recordings"]) / f"{request['session_id']}{TRANSCRIPTS_RECORDING_SUFFIX}"
    return json.loads(recording.read_text(encoding="utf-8"))


def answer(operation: str, request: dict) -> dict:
    if operation == "probe":
        return _probe(request)
    if operation == "launch-argv":
        return _build_launch(request)
    if operation == "parse-result":
        return _replay_result(request)
    if operation == "actions" and operation in _read_list_setting(request, "operations"):
        return _read_actions(request)
    if operation == "transcripts" and operation in _read_list_setting(request, "operations"):
        return _replay_transcripts(request)
    raise BrigadeError(f"the fake client adapter does not answer {operation}")
