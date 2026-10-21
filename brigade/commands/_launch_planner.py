import argparse

from brigade.commands.run import run
from brigade.runtime import Runtime
from brigade.waves.read_planner_run import PLANNER_PROCEDURE

PLANNER_SLOT = "plan"
LAUNCH_FIELDS = ("run", "warnings")


def launch_planner(runtime: Runtime, project: str, request: str) -> dict:
    planning = argparse.Namespace(
        procedure=PLANNER_PROCEDURE,
        slot=PLANNER_SLOT,
        project=project,
        cwd=None,
        brief=None,
        arguments=(f"request={request}",),
        run_id=None,
        wave=None,
        task=None,
        detach=True,
        resume=False,
    )
    launched = run(planning, runtime)
    return {field: launched[field] for field in LAUNCH_FIELDS if field in launched}
