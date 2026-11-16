from brigade.checks._read_pull_request import read_pull_request
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_check_runs import check_check_runs


def check(subject: dict, runtime: Runtime) -> dict:
    return {
        "schema_version": CHECK_DOCUMENT_SCHEMA_VERSION,
        **check_check_runs(read_pull_request(subject)["check_runs"]),
    }
