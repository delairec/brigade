from pathlib import Path

from brigade.checks._read_pull_request import read_pull_request
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_corpus_at_head import check_corpus_at_head


def check(subject: dict, runtime: Runtime) -> dict:
    head_tree = Path(read_pull_request(subject)["head_tree"])
    return {"schema_version": CHECK_DOCUMENT_SCHEMA_VERSION, **check_corpus_at_head(runtime.run_process, head_tree)}
