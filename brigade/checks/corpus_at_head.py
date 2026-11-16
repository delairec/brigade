from pathlib import Path

from brigade.checks._read_branch import read_branch
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_corpus_at_head import check_corpus_at_head


def check(subject: dict, runtime: Runtime) -> dict:
    head_tree = Path(read_branch(subject)["head_tree"])
    return {"schema_version": CHECK_DOCUMENT_SCHEMA_VERSION, **check_corpus_at_head(runtime.run_process, head_tree)}
