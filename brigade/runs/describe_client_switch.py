from brigade.ledger.run_client_switched import RunClientSwitched
from brigade.runs.plan_run import RunPlan
from brigade.system.parse_configuration import Configuration

RATE_LIMIT_REASON = "rate_limit"
RESET_REASON = "reset"
REASONING_FIELD = "reasoning"


def _read_model(reasoning: dict, level: str) -> str | None:
    row = reasoning.get(level)
    return None if row is None else row.model


def describe_client_switch(
    plan: RunPlan, regular_client: str, configuration: Configuration
) -> RunClientSwitched | None:
    client_left = plan.resumed_client or regular_client
    if client_left == plan.client:
        return None
    if plan.on_fallback:
        reasoning_left, reason = configuration.reasoning, RATE_LIMIT_REASON
    elif configuration.fallback is not None and client_left == configuration.fallback.client:
        reasoning_left, reason = configuration.fallback.reasoning, RESET_REASON
    else:
        return None
    level = plan.role.front_matter[REASONING_FIELD]
    return RunClientSwitched(
        run=plan.run_id,
        client_left=client_left,
        model_left=_read_model(reasoning_left, level),
        client_taken=plan.client,
        model_taken=_read_model(plan.configuration.reasoning, level),
        reason=reason,
    )
