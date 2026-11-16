from pathlib import Path

from brigade.checks._read_branch import read_branch
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_acceptance import AcceptanceFacts, check_acceptance


def check(subject: dict, runtime: Runtime) -> dict:
    facts = read_branch(subject)
    acceptance = AcceptanceFacts(head_tree=Path(facts["checkout"]), commands=tuple(map(tuple, facts["acceptance"])))
    return {"schema_version": CHECK_DOCUMENT_SCHEMA_VERSION, **check_acceptance(runtime.run_process, acceptance)}
