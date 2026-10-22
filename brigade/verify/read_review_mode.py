from brigade.corpus.read_entities import read_entities
from brigade.registry.read_policy_field import read_policy_field
from brigade.runtime import Runtime

POLICY_TYPE = "POLICY"
REVIEW_FIELD = "REVIEW"
VERDICT_REVIEW = "verdict"
APPROVAL_REVIEW = "approval"


def read_review_mode(runtime: Runtime, project: str) -> str:
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    return read_policy_field(policies, project, REVIEW_FIELD, VERDICT_REVIEW)
