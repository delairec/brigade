from brigade.verify.judge_findings import judge_findings

NAME = "checks"
SUCCESSFUL = "success"


def check_check_runs(check_runs: list[dict]) -> dict:
    return judge_findings(
        NAME, [f"{run['name']}: {run['verdict']}" for run in check_runs if run["verdict"] != SUCCESSFUL]
    )
