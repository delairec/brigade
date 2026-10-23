import json
from datetime import UTC, datetime
from pathlib import Path

from brigade.adapters.clients.describe_unreadable_output import describe_unreadable_output
from brigade.errors import BrigadeError
from brigade.runs.compose_brief import PROGRESS_SECTION
from brigade.system.instant_formats import ISO_INSTANT_FORMAT

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
SLOW_CLIENT_SETTINGS = ("delay", "progress", "interval")
TRANSCRIPTS_RECORDING_SUFFIX = ".transcripts.json"
RESUMED_RECORDING_SUFFIX = ".resumed.json"
RESUMED_BRIEF_OPENING = f"# {PROGRESS_SECTION}\n"
ATTRIBUTION_SETTING = "attribution"
RESUME_OPERATION = "resume"
PLAYS_SETTING = "plays"


def _read_list_setting(request: dict, name: str) -> list[str]:
    declared = request.get("settings", {}).get(name, "")
    return [value.strip() for value in declared.split(SETTING_SEPARATOR) if value.strip()]


def _answer_attribution(request: dict) -> dict:
    if ATTRIBUTION_SETTING not in request.get("settings", {}):
        return {}
    return {"attribution": _read_list_setting(request, ATTRIBUTION_SETTING)}


def _probe(request: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "client": CLIENT_NAME,
        "version_argv": None,
        "operations": [*REPLAYED_OPERATIONS, *_read_list_setting(request, "operations")],
        "features": _read_list_setting(request, "features"),
        "models": {},
        **_answer_attribution(request),
    }


def _read_soft_limit(request: dict):
    if request["stop_at"] is None or GRACEFUL_STOP not in _read_list_setting(request, "features"):
        return None
    return str(round(datetime.strptime(request["stop_at"], ISO_INSTANT_FORMAT).replace(tzinfo=UTC).timestamp()))


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


def _choose_recording(recordings: str, request: dict) -> str:
    role = request["role"]["name"]
    resumed = Path(recordings) / f"{role}{RESUMED_RECORDING_SUFFIX}"
    if resumed.exists() and request["brief"].startswith(RESUMED_BRIEF_OPENING):
        return str(resumed)
    return f"{recordings}/{role}.json"


def _find_play(request: dict) -> Path | None:
    plays = request["settings"].get(PLAYS_SETTING)
    if plays is None:
        return None
    play = Path(plays) / request["role"]["name"]
    return play if play.exists() else None


def _build_launch(request: dict) -> dict:
    recordings = request["settings"].get("recordings")
    if recordings is None:
        raise BrigadeError("the fake client adapter needs recordings in the table [clients.fake] of config.toml")
    recording = _choose_recording(recordings, request)
    play = _find_play(request)
    if play is not None:
        argv, stdin = [str(play), recording], request["brief"]
    else:
        argv, stdin = _build_argv(request["settings"], recording, _read_soft_limit(request)), None
    return {
        "schema_version": SCHEMA_VERSION,
        "argv": argv,
        "environment": {},
        "stdin": stdin,
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
    if operation == "resume-argv" and RESUME_OPERATION in _read_list_setting(request, "operations"):
        return _build_launch(request)
    if operation == "parse-result":
        return _replay_result(request)
    if operation == "actions" and operation in _read_list_setting(request, "operations"):
        return _read_actions(request)
    if operation == "transcripts" and operation in _read_list_setting(request, "operations"):
        return _replay_transcripts(request)
    raise BrigadeError(f"the fake client adapter does not answer {operation}")
