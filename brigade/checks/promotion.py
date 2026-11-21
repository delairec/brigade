from pathlib import Path

from brigade.checks._read_pull_request import read_pull_request
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_promotion import PromotionFacts, check_promotion


def check(subject: dict, runtime: Runtime) -> dict:
    facts = read_pull_request(subject)
    promotion = PromotionFacts(
        head_tree=Path(facts["head_tree"]),
        repository_tree=Path(facts["checkout"]),
        task=facts["task"],
        pr=facts["pr"],
        changed=tuple(changed_file["path"] for changed_file in facts["changed"]),
    )
    return {"schema_version": CHECK_DOCUMENT_SCHEMA_VERSION, **check_promotion(runtime.run_process, promotion)}
