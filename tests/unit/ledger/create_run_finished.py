from brigade.ledger.run_finished import RunFinished
from brigade.system.token_usage import TokenUsage


def create_run_finished(
    run: str,
    segment: int = 1,
    procedure: str = "awawa-task",
    client: str = "claude-code",
    main_turns: int | None = None,
    outcome: str = "succeeded",
    error_class: str | None = None,
    wave: str | None = None,
    task: str | None = None,
    turns_to_first_edit: int | None = None,
    slot: str = "build",
    duration_ms: int | None = 1000,
    usage: TokenUsage | None = None,
    cost_usd: float | None = None,
    oversized_output_turns: int | None = None,
) -> RunFinished:
    return RunFinished(
        run=run,
        segment=segment,
        procedure=procedure,
        slot=slot,
        role="builder",
        client=client,
        project="tidepool",
        session=None,
        main_turns=main_turns,
        total_turns=None,
        duration_ms=duration_ms,
        usage=usage,
        outcome=outcome,
        error_class=error_class,
        exit=None,
        wave=wave,
        task=task,
        nulls={},
        turns_to_first_edit=turns_to_first_edit,
        oversized_output_turns=oversized_output_turns,
        cost_usd=cost_usd,
    )
