from brigade.checks._read_pull_request import read_pull_request
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_body import check_body


def check(subject: dict, runtime: Runtime) -> dict:
    return {"schema_version": CHECK_DOCUMENT_SCHEMA_VERSION, **check_body(read_pull_request(subject)["body"])}
