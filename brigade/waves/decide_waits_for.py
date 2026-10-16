from brigade.runtime import Runtime
from brigade.waves.read_plan_review import ASKING_REVIEW, read_plan_review

PLANNED_STATUS = "planned"
WAVE_START = "brigade wave start"
NEXT_TICK = "the next tick"


def decide_waits_for(runtime: Runtime, request: dict) -> str | None:
    if request["status"] != PLANNED_STATUS:
        return None
    return WAVE_START if read_plan_review(runtime, request["project"]) == ASKING_REVIEW else NEXT_TICK
