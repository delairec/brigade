from brigade.system.validate_document import Field

SCHEMA_VERSION = Field(kinds=(int,), values=(1,))
TEXT = Field(kinds=(str,))
OPTIONAL_TEXT = Field(kinds=(str,), nullable=True)
COUNT = Field(kinds=(int,))
OPTIONAL_COUNT = Field(kinds=(int,), nullable=True)
ARGV = Field(kinds=(list,), items=TEXT, non_empty=True)

ROLE = Field(
    kinds=(dict,),
    fields={
        "name": TEXT,
        "package": TEXT,
        "capabilities": Field(kinds=(list,), items=Field(kinds=(str,), values=("read", "write", "shell", "net"))),
        "reasoning": Field(kinds=(str,), values=("deepest", "deep", "standard", "light")),
        "budget": COUNT,
    },
)
LAUNCH_REQUEST = {"schema_version": SCHEMA_VERSION, "worktree": TEXT, "brief": TEXT, "role": ROLE}

CLIENT_REQUEST_SHAPES = {
    "probe": {"schema_version": SCHEMA_VERSION},
    "launch-argv": LAUNCH_REQUEST,
    "resume-argv": {**LAUNCH_REQUEST, "session_id": TEXT},
    "parse-result": {"schema_version": SCHEMA_VERSION, "exit_code": COUNT, "stdout": TEXT, "stderr": TEXT},
    "transcripts": {"schema_version": SCHEMA_VERSION, "session_id": TEXT, "worktree": TEXT},
}

COMMAND_ANSWER = {
    "schema_version": SCHEMA_VERSION,
    "argv": ARGV,
    "environment": Field(kinds=(dict,)),
    "stdin": OPTIONAL_TEXT,
}

CLIENT_ANSWER_SHAPES = {
    "probe": {
        "schema_version": SCHEMA_VERSION,
        "client": TEXT,
        "version_argv": Field(kinds=(list,), nullable=True, items=TEXT, non_empty=True),
        "operations": Field(
            kinds=(list,), items=Field(kinds=(str,), values=("probe", "launch", "result", "resume", "transcripts"))
        ),
        "features": Field(kinds=(list,), items=Field(kinds=(str,), values=("step_count", "tool_grants", "reset_hour"))),
        "models": Field(kinds=(dict,)),
    },
    "launch-argv": COMMAND_ANSWER,
    "resume-argv": COMMAND_ANSWER,
    "parse-result": {
        "schema_version": SCHEMA_VERSION,
        "outcome": Field(kinds=(str,), values=("done", "failed")),
        "steps": OPTIONAL_COUNT,
        "usage": Field(
            kinds=(dict,),
            nullable=True,
            fields={
                "input_tokens": COUNT,
                "output_tokens": COUNT,
                "cache_creation_input_tokens": COUNT,
                "cache_read_input_tokens": COUNT,
            },
        ),
        "session_id": OPTIONAL_TEXT,
        "duration_ms": OPTIONAL_COUNT,
        "error_class": Field(
            kinds=(str,), nullable=True, values=("rate_limit", "turn_limit", "execution", "unreadable_output")
        ),
        "reset": Field(kinds=(dict,), nullable=True, fields={"hour": TEXT, "timezone": OPTIONAL_TEXT}),
        "message": OPTIONAL_TEXT,
    },
    "transcripts": {
        "schema_version": SCHEMA_VERSION,
        "messages": Field(
            kinds=(list,),
            items=Field(
                kinds=(dict,),
                fields={
                    "role": Field(kinds=(str,), values=("user", "assistant")),
                    "timestamp": OPTIONAL_TEXT,
                    "content": Field(kinds=(str, list)),
                },
            ),
        ),
    },
}
