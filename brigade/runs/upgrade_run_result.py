from brigade.runs.describe_finished import NOT_IN_A_WAVE
from brigade.runs.run_record import RunRecord
from brigade.system.client_shapes import CLIENT_ANSWER_SHAPES
from brigade.system.validate_document import Field

RESULT_SCHEMA_VERSION_1 = 1
SCHEMA_1_SHAPE = {
    **{key: field for key, field in CLIENT_ANSWER_SHAPES["parse-result"].items() if key != "cost_usd"},
    "outcome": Field(
        kinds=(str,),
        values=(
            "done",
            "failed",
            "handed_over",
            "blocked",
            "undeclared",
            "wall_limit",
            "turn_limit",
            "soft_limit",
            "stopped",
        ),
    ),
}
FIGURE_OF_THE_CLIENT = "result.json of schema 1 kept the figure of the client, not the measure of brigade"
NO_REASON_KEPT = "result.json of schema 1 kept no reason"
REASONS = {
    "main_steps": FIGURE_OF_THE_CLIENT,
    "total_steps": FIGURE_OF_THE_CLIENT,
    "duration_ms": FIGURE_OF_THE_CLIENT,
    "wave": NOT_IN_A_WAVE,
    "task": NOT_IN_A_WAVE,
}
OPTIONAL_FIELDS = ("reset", "message")


def upgrade_run_result(document: dict, record: RunRecord, segment: int) -> dict:
    finished = {
        "run": record.run,
        "segment": segment,
        "procedure": record.procedure,
        "slot": record.slot,
        "role": record.role,
        "client": record.client,
        "project": record.project,
        "session": document["session_id"],
        "main_steps": None,
        "total_steps": None,
        "duration_ms": None,
        "usage": document["usage"],
        "outcome": document["outcome"],
        "error_class": document["error_class"],
        "exit": None,
        "wave": None,
        "task": None,
    }
    nulls = {field: REASONS.get(field, NO_REASON_KEPT) for field, value in finished.items() if value is None}
    return {**finished, "nulls": nulls, **{field: document[field] for field in OPTIONAL_FIELDS}}
