import json
import math
import re
from pathlib import Path

from brigade.adapters.clients.describe_unreadable_output import describe_unreadable_output
from brigade.errors import BrigadeError

SCHEMA_VERSION = 1
CLIENT_NAME = "claude-code"
EXECUTABLE = "claude"
UNATTENDED_OPTIONS = ("--print", "--output-format", "stream-json", "--verbose", "--permission-mode", "dontAsk")
REASONING_DEFAULTS = {
    "deepest": {"model": "fable", "effort": "max"},
    "deep": {"model": "fable", "effort": "high"},
    "standard": {"model": "opus", "effort": "high"},
    "light": {"model": "sonnet", "effort": "medium"},
}
CAPABILITY_TOOLS = {
    "read": ("Read", "Glob", "Grep"),
    "write": ("Edit", "Write", "NotebookEdit"),
    "shell": ("Bash",),
    "net": ("WebFetch", "WebSearch"),
}
PROGRESS_FILE_TOOLS = ("Write", "Edit")
TURN_MARGIN_DIVISOR = 4
USAGE_COUNTERS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
RATE_LIMIT_PHRASES = ("limit reached", "hit your limit", "usage limit", "rate limit")
RESET_PATTERN = re.compile(r"resets (?:at )?(\d{1,2})(?::(\d{2}))?(am|pm)?(?: \(([^)]+)\))?", re.IGNORECASE)
ERROR_SUBTYPE_PREFIX = "error"
TRANSCRIPT_MESSAGE_TYPES = ("user", "assistant")
IDENTIFYING_ARGUMENTS = ("file_path", "command", "pattern", "path", "url", "query")


def _bind_models(request: dict) -> dict:
    return {
        level: request["reasoning_table"].get(level, default_row)["model"]
        for level, default_row in REASONING_DEFAULTS.items()
    }


def _probe(request: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "client": CLIENT_NAME,
        "version_argv": [EXECUTABLE, "--version"],
        "operations": ["probe", "launch", "result", "resume", "transcripts", "actions"],
        "features": ["step_count", "tool_grants", "reset_hour"],
        "models": _bind_models(request),
    }


def _build_role_options(request: dict) -> list[str]:
    role = request["role"]
    reasoning = request["reasoning_table"].get(role["reasoning"], REASONING_DEFAULTS[role["reasoning"]])
    max_turns = role["budget"] + math.ceil(role["budget"] / TURN_MARGIN_DIVISOR)
    tools = [tool for capability in role["capabilities"] for tool in CAPABILITY_TOOLS[capability]]
    progress_rules = [f"{tool}(/{request['progress_file']})" for tool in PROGRESS_FILE_TOOLS]
    return [
        "--model",
        reasoning["model"],
        "--effort",
        reasoning["effort"],
        "--max-turns",
        str(max_turns),
        "--append-system-prompt-file",
        role["package_file"],
        "--allowedTools",
        ",".join([*tools, *progress_rules]),
    ]


def _build_command(request: dict, session_options: list[str]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "argv": [EXECUTABLE, *UNATTENDED_OPTIONS, *session_options, *_build_role_options(request)],
        "environment": {},
        "stdin": request["brief"],
    }


def _read_event(line: str) -> dict:
    try:
        event = json.loads(line)
    except ValueError:
        return {}
    if not isinstance(event, dict):
        return {}
    return event


def _read_result_object(stdout: str):
    events = (_read_event(line) for line in reversed(stdout.splitlines()))
    return next((event for event in events if event.get("type") == "result"), None)


def _read_usage(result: dict):
    usage = result.get("usage")
    if not isinstance(usage, dict):
        return None
    return {counter: usage.get(counter, 0) for counter in USAGE_COUNTERS}


def _format_hour(hour: str, minutes: str, meridiem: str) -> str:
    hour_of_day = int(hour)
    if meridiem is not None:
        hour_of_day = hour_of_day % 12 + (12 if meridiem.lower() == "pm" else 0)
    return f"{hour_of_day:02d}:{minutes or '00'}"


def _read_reset(message: str):
    match = RESET_PATTERN.search(message)
    if match is None:
        return None
    hour, minutes, meridiem, timezone = match.groups()
    return {"hour": _format_hour(hour, minutes, meridiem), "timezone": timezone}


def _names_rate_limit(message) -> bool:
    return message is not None and any(phrase in message.lower() for phrase in RATE_LIMIT_PHRASES)


def _classify_error(result: dict, message):
    if result.get("subtype") == "error_max_turns":
        return "turn_limit"
    if result.get("is_error") and _names_rate_limit(message):
        return "rate_limit"
    if result.get("is_error") or str(result.get("subtype", "")).startswith(ERROR_SUBTYPE_PREFIX):
        return "execution"
    return None


def _parse_result(request: dict) -> dict:
    result = _read_result_object(request["stdout"])
    if result is None:
        return describe_unreadable_output(request["stderr"])
    message = result.get("result")
    error_class = _classify_error(result, message)
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": "done" if error_class is None else "failed",
        "steps": result.get("num_turns"),
        "usage": _read_usage(result),
        "session_id": result.get("session_id"),
        "duration_ms": result.get("duration_ms"),
        "error_class": error_class,
        "reset": _read_reset(message) if error_class == "rate_limit" else None,
        "message": None if error_class is None else message,
    }


def _summarise_tool_call(item: dict) -> str:
    tool_input = item["input"]
    argument = next((tool_input[name] for name in IDENTIFYING_ARGUMENTS if name in tool_input), None)
    return item["name"] if argument is None else f"{item['name']} {argument}"


def _read_content_actions(event: dict) -> list[dict]:
    actions = []
    for item in event["message"]["content"]:
        if item.get("type") == "tool_use":
            actions.append({"kind": "tool", "summary": _summarise_tool_call(item)})
        elif item.get("type") == "text":
            actions.append({"kind": "text", "summary": item["text"].partition("\n")[0]})
    return actions


def _read_event_actions(event: dict) -> list[dict]:
    if event.get("type") == "assistant":
        return _read_content_actions(event)
    if event.get("type") == "result":
        outcome = "done" if _classify_error(event, event.get("result")) is None else "failed"
        return [{"kind": "result", "summary": outcome}]
    return []


def _read_actions(request: dict) -> dict:
    events = [_read_event(line) for line in request["output"].splitlines()]
    actions = [action for event in events for action in _read_event_actions(event)]
    return {"schema_version": SCHEMA_VERSION, "actions": actions}


def _name_project_directory(worktree: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", worktree)


def _read_transcripts(request: dict) -> dict:
    session_id = request["session_id"]
    project_directory = Path(request["home"]) / ".claude" / "projects" / _name_project_directory(request["worktree"])
    path = project_directory / f"{session_id}.jsonl"
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise BrigadeError(f"no transcript of session {session_id} at {path}") from None
    entries = [json.loads(line) for line in content.splitlines() if line.strip()]
    messages = [
        {"role": entry["message"]["role"], "timestamp": entry.get("timestamp"), "content": entry["message"]["content"]}
        for entry in entries
        if entry.get("type") in TRANSCRIPT_MESSAGE_TYPES
    ]
    return {"schema_version": SCHEMA_VERSION, "messages": messages}


def answer(operation: str, request: dict) -> dict:
    if operation == "probe":
        return _probe(request)
    if operation == "launch-argv":
        return _build_command(request, [])
    if operation == "resume-argv":
        return _build_command(request, ["--resume", request["session_id"]])
    if operation == "parse-result":
        return _parse_result(request)
    if operation == "transcripts":
        return _read_transcripts(request)
    if operation == "actions":
        return _read_actions(request)
    raise BrigadeError(f"the claude-code client adapter does not answer {operation}")
