import dataclasses
from pathlib import Path

from brigade.adapters.documents import markdown
from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.system.read_configuration import Configuration

RUN_ID = "20261019T090000Z-c0ffee"


def create_run_plan(root: Path, **changes) -> RunPlan:
    run_directory = root / "state" / "runs" / RUN_ID
    plan = RunPlan(
        run_id=RUN_ID,
        run_directory=run_directory,
        procedure=Procedure(
            name="build-task",
            location="built-in",
            argument="build-task",
            capabilities=("read", "write"),
            budget=40,
            body="Deliver the task.",
        ),
        slot="build",
        role=ResolvedRole(
            slot="build",
            role="builder",
            source="built-in",
            front_matter={"name": "builder", "reasoning": "standard"},
            body="You build.",
        ),
        client="fake",
        client_adapter=None,
        document=markdown,
        progress_file=run_directory / "progress.md",
        configuration=Configuration(),
        project=None,
        cwd=root / "project",
        worktree=root / "project",
        disposable_worktree=False,
        capabilities=("read", "write"),
        wall_limit_s=1500.0,
        arguments={},
        wave=None,
        task=None,
        brief_path=None,
        brief=None,
        counts_steps=True,
        reads_actions=False,
        reads_transcripts=False,
        handovers=0,
        warnings=(),
    )
    return dataclasses.replace(plan, **changes)
