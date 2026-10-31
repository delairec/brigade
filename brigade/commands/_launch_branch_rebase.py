import argparse

from brigade.commands.run import run
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.waves.rebase_milestone_branches import BranchRebaseRun

REBASE_PROCEDURE = "rebase-on-base"
REBASE_SLOT = "rebase"


def launch_branch_rebase(runtime: Runtime, configuration: Configuration, rebase: BranchRebaseRun) -> None:
    rebasing = argparse.Namespace(
        procedure=configuration.procedures.get(REBASE_SLOT, REBASE_PROCEDURE),
        slot=REBASE_SLOT,
        project=rebase.project,
        cwd=str(rebase.worktree),
        brief=None,
        arguments=(f"base={rebase.base}",),
        run_id=None,
        wave=rebase.wave,
        task=None,
        detach=True,
        resume=False,
    )
    run(rebasing, runtime)
