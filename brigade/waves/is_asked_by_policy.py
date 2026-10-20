from brigade.corpus.read_entities import read_entities
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime

POLICY_TYPE = "POLICY"
ASKING = "ask"


def is_asked_by_policy(runtime: Runtime, project: str, field_name: str) -> bool:
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    return any(
        read_project_field(policy, "PROJECT") == f"@PROJECT.{project}"
        and read_project_field(policy, field_name) == ASKING
        for policy in policies
    )
