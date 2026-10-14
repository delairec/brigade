from brigade.corpus.read_entities import read_entities
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime

PLANNED_STATUS = "planned"
POLICY_TYPE = "POLICY"
ASKING_REVIEW = "ask"
WAVE_START = "brigade wave start"
NEXT_TICK = "the next tick"


def decide_waits_for(runtime: Runtime, request: dict) -> str | None:
    if request["status"] != PLANNED_STATUS:
        return None
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    asking = any(
        read_project_field(policy, "PROJECT") == f"@PROJECT.{request['project']}"
        and read_project_field(policy, "PLAN_REVIEW") == ASKING_REVIEW
        for policy in policies
    )
    return WAVE_START if asking else NEXT_TICK
