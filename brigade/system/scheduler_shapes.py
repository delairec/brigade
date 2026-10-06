from brigade.system.validate_document import Field

SCHEMA_VERSION = Field(kinds=(int,), values=(1,))
TEXT = Field(kinds=(str,))
OPTIONAL_TEXT = Field(kinds=(str,), nullable=True)
UNIT_FILES = Field(kinds=(list,), items=TEXT)

SCHEDULER_ANSWER_SHAPES = {
    "install": {
        "schema_version": SCHEMA_VERSION,
        "scheduler": TEXT,
        "unit_files": UNIT_FILES,
        "cron_line": OPTIONAL_TEXT,
        "keep_running": OPTIONAL_TEXT,
    },
    "read_status": {
        "schema_version": SCHEMA_VERSION,
        "installed": Field(kinds=(bool,)),
        "unit_files": UNIT_FILES,
        "cron_line": OPTIONAL_TEXT,
        "next_activation": OPTIONAL_TEXT,
    },
}
