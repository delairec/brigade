from brigade.corpus.read_entities import read_entities
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime

POLICY_TYPE = "POLICY"
VERDICT_REVIEW = "verdict"
APPROVAL_REVIEW = "approval"


def read_review_mode(runtime: Runtime, project: str) -> str:
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    modes = [
        read_project_field(policy, "REVIEW")
        for policy in policies
        if read_project_field(policy, "PROJECT") == f"@PROJECT.{project}"
    ]
    return next((mode for mode in modes if mode is not None), VERDICT_REVIEW)
