from brigade.ledger.run_finished import RunFinished


def create_run_finished(
    run: str,
    segment: int = 1,
    procedure: str = "awawa-task",
    client: str = "claude-code",
    main_steps: int | None = None,
    outcome: str = "succeeded",
    error_class: str | None = None,
    wave: str | None = None,
    task: str | None = None,
    steps_to_first_edit: int | None = None,
) -> RunFinished:
    return RunFinished(
        run=run,
        segment=segment,
        procedure=procedure,
        slot="build",
        role="builder",
        client=client,
        project="tidepool",
        session=None,
        main_steps=main_steps,
        total_steps=None,
        duration_ms=1000,
        usage=None,
        outcome=outcome,
        error_class=error_class,
        exit=None,
        wave=wave,
        task=task,
        nulls={},
        steps_to_first_edit=steps_to_first_edit,
    )
