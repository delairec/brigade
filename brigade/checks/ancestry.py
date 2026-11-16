from pathlib import Path

from brigade.checks._read_pull_request import read_pull_request
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_ancestry import AncestryFacts, check_ancestry


def check(subject: dict, runtime: Runtime) -> dict:
    facts = read_pull_request(subject)
    ancestry = AncestryFacts(
        repository=Path(facts["repository"]),
        base_branch=facts["base_branch"],
        base_head=facts["base_head"],
        head=facts["head"],
    )
    return {"schema_version": CHECK_DOCUMENT_SCHEMA_VERSION, **check_ancestry(runtime.run_process, ancestry)}
