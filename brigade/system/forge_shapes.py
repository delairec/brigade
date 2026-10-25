from brigade.system.validate_document import Field

FORGE_ANSWER_SHAPES = {
    "describe_account": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "login": Field(kinds=(str,), nullable=True),
    },
    "read_login_environment": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "environment": Field(kinds=(dict,), nullable=True),
    },
    "find_pull_request": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "pull_request": Field(kinds=(dict,), nullable=True),
    },
    "list_pull_requests": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "pull_requests": Field(kinds=(list,), items=Field(kinds=(dict,))),
    },
    "read_pull_request": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "pull_request": Field(kinds=(dict,)),
    },
    "read_check_logs": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "logs": Field(kinds=(list,), items=Field(kinds=(dict,))),
    },
    "list_review_threads": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "threads": Field(kinds=(list,), items=Field(kinds=(dict,))),
    },
    "list_check_runs": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "check_runs": Field(kinds=(list,), items=Field(kinds=(dict,))),
    },
    "read_job_steps": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "steps": Field(kinds=(list,), nullable=True, items=Field(kinds=(dict,))),
    },
    "reply_review_thread": {
        "schema_version": Field(kinds=(int,), values=(1,)),
    },
}
