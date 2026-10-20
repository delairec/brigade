from brigade.runtime import Runtime
from brigade.waves.is_asked_by_policy import ASKING, is_asked_by_policy

ASKING_REVIEW = ASKING
AUTOMATIC_REVIEW = "auto"


def read_plan_review(runtime: Runtime, project: str) -> str:
    return ASKING_REVIEW if is_asked_by_policy(runtime, project, "PLAN_REVIEW") else AUTOMATIC_REVIEW
