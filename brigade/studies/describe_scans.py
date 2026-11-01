from brigade.studies.convert_study import Study

COLLECTOR_BY_SCAN = (
    ("corpus_lint", "corpus-lint"),
    ("corpus_fmt", "corpus-fmt"),
    ("stale_branches", "stale-branches"),
    ("worktrees", "stale-worktrees"),
)
SLOT_WITHOUT_JUDGING_RUN = "none"
ONCE_A_DAY = "24h"
INBOX_OUTPUT = "inbox"
ANSWER_TYPE = "ANSWER"
ACTIVE_STATUS = "active"


def describe_scans(project: str) -> tuple[Study, ...]:
    return tuple(
        Study(
            name=f"{scan}_{project}",
            project=project,
            question=None,
            collectors=(collector,),
            slot=SLOT_WITHOUT_JUDGING_RUN,
            every=ONCE_A_DAY,
            output=INBOX_OUTPUT,
            answer_type=ANSWER_TYPE,
            status=ACTIVE_STATUS,
        )
        for scan, collector in COLLECTOR_BY_SCAN
    )
