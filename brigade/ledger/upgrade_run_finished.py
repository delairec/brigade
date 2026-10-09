from brigade.system.validate_document import KIND_NAMES, Field, validate_document

NO_SUB_AGENT_COUNTED = "recorded under schema 1, which counts no sub-agent"
SCHEMA_1_SHAPE = {"steps": Field(tuple(KIND_NAMES), nullable=True), "nulls": Field((dict,))}


def _rename_steps(field: str) -> str:
    return "main_steps" if field == "steps" else field


def upgrade_run_finished(record: dict) -> dict:
    validate_document(record, SCHEMA_1_SHAPE)
    nulls = {_rename_steps(field): reason for field, reason in record["nulls"].items()}
    return {
        **{key: value for key, value in record.items() if key != "steps"},
        "main_steps": record["steps"],
        "total_steps": None,
        "nulls": {**nulls, "total_steps": NO_SUB_AGENT_COUNTED},
    }
