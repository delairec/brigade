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
}
