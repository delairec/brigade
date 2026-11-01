from brigade.studies.convert_study import Study


def create_scan(name: str, collector: str) -> Study:
    return Study(
        name=name,
        project="oak",
        question=None,
        collectors=(collector,),
        slot="none",
        every="24h",
        output="inbox",
        answer_type="ANSWER",
        status="active",
    )


SCANS_OF_OAK = (
    create_scan("corpus_lint_oak", "corpus-lint"),
    create_scan("corpus_fmt_oak", "corpus-fmt"),
    create_scan("stale_branches_oak", "stale-branches"),
    create_scan("worktrees_oak", "stale-worktrees"),
)
