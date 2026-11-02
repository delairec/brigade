from brigade.ledger.run_finished import RunFinished
from brigade.system.token_usage import TokenUsage


def create_run_finished(run: str, session: str | None, task: str | None = "B42") -> RunFinished:
    return RunFinished(
        run=run,
        segment=1,
        procedure="build-task",
        slot="build",
        role="ada",
        client="vibe",
        project="oak",
        session=session,
        main_steps=12,
        total_steps=12,
        duration_ms=60000,
        usage=TokenUsage(
            input_tokens=10, output_tokens=200, cache_creation_input_tokens=0, cache_read_input_tokens=3000
        ),
        outcome="done",
        error_class=None,
        exit=0,
        wave="oak_w3",
        task=task,
        nulls={},
        cost_usd=0.42,
    )
