import json
import math
import re
from pathlib import Path

from brigade.adapters.clients.describe_unreadable_output import describe_unreadable_output
from brigade.errors import BrigadeError

SCHEMA_VERSION = 1
CLIENT_NAME = "vibe"
EXECUTABLE = "vibe"
UNATTENDED_OPTIONS = ("-p", "--output", "streaming", "--trust", "--auto-approve")
REASONING_LEVELS = ("deepest", "deep", "standard", "light")
UNBOUND_LEVEL_ROW = {"model": "mistral-medium-3.5"}
RUST_CLI = {"VIBE_CLI": "rust"}
CAPABILITY_TOOLS = {
    "read": ("read_file", "grep"),
    "write": ("edit", "write_file"),
    "shell": ("bash",),
    "net": ("web_fetch", "web_search"),
}
PROGRESS_FILE_TOOL = "write_file"
TURN_MARGIN_DIVISOR = 4
PACKAGE_SEPARATOR = "\n---\n"
SESSION_STORE = (".vibe", "logs", "session", "unified")
JOURNAL_FILES = "*.jsonl"
CUT_EXIT_CODE = 1
RATE_LIMIT_PATTERN = re.compile(r"rate limit", re.IGNORECASE)
BLOCKED_OUTCOME = "blocked"
END_DECLARATIONS = {f"brigade-end: {outcome}": outcome for outcome in ("done", "handed_over", BLOCKED_OUTCOME)}
UNDECLARED = "undeclared"
NO_CACHE_CREATION = 0


def _bind_model(request: dict, level: str) -> str:
    return request["reasoning_table"].get(level, UNBOUND_LEVEL_ROW)["model"]


def _probe(request: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "client": CLIENT_NAME,
        "version_argv": [EXECUTABLE, "--version"],
        "operations": ["probe", "launch", "result", "transcripts"],
        "features": ["step_count", "tool_grants"],
        "models": {level: _bind_model(request, level) for level in REASONING_LEVELS},
    }


def _grant_tools(capabilities: list[str]) -> list[str]:
    tools = [tool for capability in capabilities for tool in CAPABILITY_TOOLS[capability]]
    granted = dict.fromkeys([*tools, PROGRESS_FILE_TOOL])
    return [option for tool in granted for option in ("--enabled-tools", tool)]


def _build_launch(request: dict) -> dict:
    role = request["role"]
    max_turns = role["budget"] + math.ceil(role["budget"] / TURN_MARGIN_DIVISOR)
    package = Path(role["package_file"]).read_text(encoding="utf-8")
    return {
        "schema_version": SCHEMA_VERSION,
        "argv": [EXECUTABLE, *UNATTENDED_OPTIONS, "--max-turns", str(max_turns), *_grant_tools(role["capabilities"])],
        "environment": {**RUST_CLI, "VIBE_ACTIVE_MODEL": _bind_model(request, role["reasoning"])},
        "stdin": f"{package}{PACKAGE_SEPARATOR}{request['brief']}",
        "session_id": None,
    }


def _read_entry(line: str) -> dict | None:
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    return entry if isinstance(entry, dict) else None


def _read_entries(stdout: str) -> list[dict] | None:
    entries = [_read_entry(line) for line in stdout.splitlines()]
    return None if None in entries else entries


def _is_final_message(entry: dict) -> bool:
    return entry["type"] == "message" and entry.get("role") == "assistant"


def _read_text(content: list[dict]) -> str:
    return "".join(part["text"] for part in content if part["type"] == "text")


def _describe_session(entries: list[dict]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "steps": sum(1 for entry in entries if _is_final_message(entry)),
        "session_id": entries[0]["sessionId"],
        "duration_ms": entries[-1]["updatedAt"] - entries[0]["createdAt"],
        "cost_usd": None,
        "reset": None,
    }


def _read_usage(home: str, session_id: str) -> dict | None:
    session = Path(home, *SESSION_STORE, session_id)
    try:
        generation = json.loads((session / "CURRENT").read_text(encoding="utf-8"))["generation"]
        state = json.loads((session / "generations" / generation / "projection-state.json").read_text(encoding="utf-8"))
        token_usage = state["snapshot"]["session"]["tokenUsage"]
        return {
            "input_tokens": token_usage["inputTokens"] - token_usage["cachedInputTokens"],
            "output_tokens": token_usage["outputTokens"],
            "cache_creation_input_tokens": NO_CACHE_CREATION,
            "cache_read_input_tokens": token_usage["cachedInputTokens"],
        }
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _read_declared_end(entries: list[dict]) -> tuple[str, str | None]:
    if not _is_final_message(entries[-1]):
        return UNDECLARED, None
    text = _read_text(entries[-1]["content"])
    outcome = END_DECLARATIONS.get(text.rstrip().rpartition("\n")[2].strip(), UNDECLARED)
    return outcome, text if outcome == BLOCKED_OUTCOME else None


def _describe_ended_session(entries: list[dict], home: str) -> dict:
    session = _describe_session(entries)
    outcome, message = _read_declared_end(entries)
    return {
        **session,
        "outcome": outcome,
        "usage": _read_usage(home, session["session_id"]),
        "error_class": None,
        "message": message,
    }


def _describe_cut_session(entries: list[dict], stderr: str) -> dict:
    return {
        **_describe_session(entries),
        "outcome": "failed",
        "usage": None,
        "error_class": "turn_limit",
        "message": describe_unreadable_output(stderr)["message"],
    }


def _describe_failure(stderr: str) -> dict:
    failure = describe_unreadable_output(stderr)
    message = failure["message"]
    if message is None:
        return failure
    return {**failure, "error_class": "rate_limit" if RATE_LIMIT_PATTERN.search(message) else "execution"}


def _parse_result(request: dict) -> dict:
    entries = _read_entries(request["stdout"])
    if entries is None:
        return describe_unreadable_output(request["stderr"])
    if request["exit_code"] == 0 and entries:
        return _describe_ended_session(entries, request["home"])
    if request["exit_code"] == CUT_EXIT_CODE and entries and entries[-1]["type"] == "effect":
        return _describe_cut_session(entries, request["stderr"])
    return _describe_failure(request["stderr"])


def _read_journal_file(path: Path) -> list[dict]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, ValueError) as error:
        raise BrigadeError(f"unreadable journal at {path}: {error}") from None


def _describe_user_message(entry: dict) -> dict:
    return {"role": "user", "timestamp": None, "content": entry["content"], "tool_calls": 0, "id": None, "usage": None}


def _describe_model_turn(result: dict) -> dict:
    parts = result["parts"]
    usage = result["usage"]
    return {
        "role": "assistant",
        "timestamp": None,
        "content": _read_text(parts),
        "tool_calls": sum(1 for part in parts if part["type"] == "tool_call"),
        "id": None,
        "usage": {
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "cache_creation_input_tokens": NO_CACHE_CREATION,
            "cache_read_input_tokens": usage["cached_input_tokens"],
        },
    }


def _describe_record(record: dict, completions: set[str]) -> list[dict]:
    payload = record["payload"]
    if record["type"] == "projection_delta":
        entries = (change.get("entry", {}) for change in payload["delta"])
        return [_describe_user_message(entry) for entry in entries if entry.get("role") == "user"]
    if record["type"] == "action_result" and payload["action_id"] in completions:
        return [_describe_model_turn(payload["result"]["result"])]
    return []


def _read_transcripts(request: dict) -> dict:
    session_id = request["session_id"]
    journal = Path(request["home"], *SESSION_STORE, session_id, "journal")
    if not journal.is_dir():
        raise BrigadeError(f"no journal of session {session_id} at {journal}")
    records = [record for path in sorted(journal.glob(JOURNAL_FILES)) for record in _read_journal_file(path)]
    completions = {
        record["payload"]["action_id"]
        for record in records
        if record["type"] == "action_intent" and record["payload"]["kind"] == "completion"
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "messages": [message for record in records for message in _describe_record(record, completions)],
        "subagents": [],
    }


def answer(operation: str, request: dict) -> dict:
    if operation == "probe":
        return _probe(request)
    if operation == "launch-argv":
        return _build_launch(request)
    if operation == "parse-result":
        return _parse_result(request)
    if operation == "transcripts":
        return _read_transcripts(request)
    raise BrigadeError(f"the vibe client adapter does not answer {operation}")
