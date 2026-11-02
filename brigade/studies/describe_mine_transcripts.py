from brigade.studies.convert_study import Study

NAME = "mine_transcripts"
EVERY_MONDAY_MORNING = "mon@09:00"


def describe_mine_transcripts() -> Study:
    return Study(
        name=NAME,
        project=None,
        question=(
            "Group the findings of the transcripts of the runs into patterns: one PATTERN entity per recurring"
            " problem of the runs, with its TITLE, STATUS new, one EVIDENCE per finding it groups opening on the"
            " fingerprint of that finding, and an ACTION, wave, constraint, order or dismiss."
        ),
        collectors=("transcript-findings",),
        slot="triage",
        every=EVERY_MONDAY_MORNING,
        output="entity:PATTERN",
        answer_type="PATTERN",
        status="active",
    )
