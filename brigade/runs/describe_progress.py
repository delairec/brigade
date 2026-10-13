from importlib.resources import files

from brigade.runs.plan_run import RunPlan

PROGRESS_DOCUMENT = "progress"
PROGRESS_SCHEMA = files("brigade.runs") / "data" / "progress.awawa.tpl"
SHELL_CAPABILITY = "shell"
PROGRESS_FRAME = (
    (
        "one entry per major step: what it did in one line, the facts it established, one line each and five at most,"
        " and the next step as the procedure names it, complete at the end"
    ),
    "a fact is what the next segment needs and no command gives back",
    (
        "never command output, a diff, the course of the step, a restatement of the brief or a fact an earlier entry"
        " holds"
    ),
    "a handover entry holds what remains, one line per step not done, and the next step",
)


def describe_progress(plan: RunPlan) -> dict:
    return {
        "document": PROGRESS_DOCUMENT,
        "path": str(plan.progress_file),
        "schema": PROGRESS_SCHEMA.read_text(encoding="utf-8"),
        "frame": list(PROGRESS_FRAME),
        "shell": SHELL_CAPABILITY in plan.capabilities,
    }
