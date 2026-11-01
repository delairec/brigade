from brigade.system.validate_document import Field

SCHEMA_VERSION = Field(kinds=(int,), values=(1,))
TEXT = Field(kinds=(str,))
OPTIONAL_TEXT = Field(kinds=(str,), nullable=True)
COUNT = Field(kinds=(int,))
OPTIONAL_COUNT = Field(kinds=(int,), nullable=True)
ARGV = Field(kinds=(list,), items=TEXT, non_empty=True)
USAGE = Field(
    kinds=(dict,),
    nullable=True,
    fields={
        "input_tokens": COUNT,
        "output_tokens": COUNT,
        "cache_creation_input_tokens": COUNT,
        "cache_read_input_tokens": COUNT,
    },
)

ROLE = Field(
    kinds=(dict,),
    fields={
        "name": TEXT,
        "package": TEXT,
        "package_file": TEXT,
        "capabilities": Field(kinds=(list,), items=Field(kinds=(str,), values=("read", "write", "shell", "net"))),
        "reasoning": Field(kinds=(str,), values=("deepest", "deep", "standard", "light")),
        "budget": COUNT,
    },
)
LAUNCH_REQUEST = {
    "schema_version": SCHEMA_VERSION,
    "worktree": TEXT,
    "brief": TEXT,
    "role": ROLE,
    "progress_file": TEXT,
    "session_id": TEXT,
    "stop_at": OPTIONAL_TEXT,
}

CLIENT_REQUEST_SHAPES = {
    "probe": {"schema_version": SCHEMA_VERSION},
    "launch-argv": LAUNCH_REQUEST,
    "resume-argv": LAUNCH_REQUEST,
    "parse-result": {"schema_version": SCHEMA_VERSION, "exit_code": COUNT, "stdout": TEXT, "stderr": TEXT},
    "transcripts": {"schema_version": SCHEMA_VERSION, "session_id": TEXT, "worktree": TEXT},
    "actions": {"schema_version": SCHEMA_VERSION, "output": TEXT},
}

COMMAND_ANSWER = {
    "schema_version": SCHEMA_VERSION,
    "argv": ARGV,
    "environment": Field(kinds=(dict,)),
    "stdin": OPTIONAL_TEXT,
    "session_id": OPTIONAL_TEXT,
}

TRANSCRIPT_MESSAGES = Field(
    kinds=(list,),
    items=Field(
        kinds=(dict,),
        fields={
            "role": Field(kinds=(str,), values=("user", "assistant")),
            "timestamp": OPTIONAL_TEXT,
            "content": Field(kinds=(str, list)),
            "tool_calls": COUNT,
            "tools": Field(kinds=(list,), items=Field(kinds=(dict,), fields={"name": TEXT, "target": OPTIONAL_TEXT})),
            "id": OPTIONAL_TEXT,
            "usage": USAGE,
        },
    ),
)

CLIENT_ANSWER_SHAPES = {
    "probe": {
        "schema_version": SCHEMA_VERSION,
        "client": TEXT,
        "version_argv": Field(kinds=(list,), nullable=True, items=TEXT, non_empty=True),
        "operations": Field(
            kinds=(list,),
            items=Field(kinds=(str,), values=("probe", "launch", "result", "resume", "transcripts", "actions")),
        ),
        "features": Field(
            kinds=(list,),
            items=Field(kinds=(str,), values=("step_count", "tool_grants", "reset_hour", "graceful_stop")),
        ),
        "models": Field(kinds=(dict,)),
        "attribution": Field(kinds=(list,), items=TEXT, optional=True),
        "edit_tools": Field(kinds=(list,), items=TEXT, optional=True),
    },
    "launch-argv": COMMAND_ANSWER,
    "resume-argv": COMMAND_ANSWER,
    "parse-result": {
        "schema_version": SCHEMA_VERSION,
        "outcome": Field(kinds=(str,), values=("done", "failed", "handed_over", "blocked", "undeclared", "soft_limit")),
        "steps": OPTIONAL_COUNT,
        "usage": USAGE,
        "session_id": OPTIONAL_TEXT,
        "duration_ms": OPTIONAL_COUNT,
        "cost_usd": Field(kinds=(int, float), nullable=True),
        "error_class": Field(
            kinds=(str,), nullable=True, values=("rate_limit", "turn_limit", "execution", "unreadable_output")
        ),
        "reset": Field(kinds=(dict,), nullable=True, fields={"hour": TEXT, "timezone": OPTIONAL_TEXT}),
        "message": OPTIONAL_TEXT,
    },
    "transcripts": {
        "schema_version": SCHEMA_VERSION,
        "messages": TRANSCRIPT_MESSAGES,
        "subagents": Field(kinds=(list,), items=Field(kinds=(dict,), fields={"messages": TRANSCRIPT_MESSAGES})),
    },
    "actions": {
        "schema_version": SCHEMA_VERSION,
        "actions": Field(
            kinds=(list,),
            items=Field(
                kinds=(dict,),
                fields={"kind": Field(kinds=(str,), values=("tool", "text", "result")), "summary": TEXT},
            ),
        ),
    },
}
