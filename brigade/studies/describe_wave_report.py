from brigade.ledger.wave_started import WaveStarted
from brigade.studies.convert_study import Study

NAME = "wave-report"
REPORT_SLOT = "report"
ANSWER_TYPE = "REPORT"
ACTIVE = "active"
TASK_REFERENCE_PREFIX = "@TASK."
ENTITY_SEPARATOR = ","


def describe_wave_report(started: WaveStarted) -> Study:
    tasks = ENTITY_SEPARATOR.join(f"{TASK_REFERENCE_PREFIX}{task}" for task in started.tasks)
    return Study(
        name=NAME,
        project=started.project,
        question=(
            f"Complete the report of the wave {started.wave}: what happened, why each parked or failed task stopped,"
            " how a tester checks each manual test, and which changes are worth reading by sampling."
        ),
        collectors=(
            f"ledger wave={started.wave}",
            "pr-list state=all",
            f"corpus ref={started.branch} entities={tasks}",
            f"git-diff-stat to={started.branch}",
        ),
        slot=REPORT_SLOT,
        every=None,
        output=f"entity:{ANSWER_TYPE}",
        answer_type=ANSWER_TYPE,
        status=ACTIVE,
        wave=started.wave,
    )
