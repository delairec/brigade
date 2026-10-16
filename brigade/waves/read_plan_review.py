from brigade.corpus.read_entities import read_entities
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime

POLICY_TYPE = "POLICY"
ASKING_REVIEW = "ask"
AUTOMATIC_REVIEW = "auto"


def read_plan_review(runtime: Runtime, project: str) -> str:
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    asking = any(
        read_project_field(policy, "PROJECT") == f"@PROJECT.{project}"
        and read_project_field(policy, "PLAN_REVIEW") == ASKING_REVIEW
        for policy in policies
    )
    return ASKING_REVIEW if asking else AUTOMATIC_REVIEW
