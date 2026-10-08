from brigade.system.validate_document import Field

FORGE_ANSWER_SHAPES = {
    "describe_account": {
        "schema_version": Field(kinds=(int,), values=(1,)),
        "login": Field(kinds=(str,), nullable=True),
    },
}
