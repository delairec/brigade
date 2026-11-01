from brigade.studies.convert_study import Study

BUILT_IN_MINE_TRANSCRIPTS = Study(
    name="mine-transcripts",
    project=None,
    question=(
        "Group the findings of the transcripts of the runs into patterns: one PATTERN entity per recurring"
        " problem of the runs, with its TITLE, STATUS new, one EVIDENCE per finding it groups opening on the"
        " fingerprint of that finding, and an ACTION, wave, constraint, order or dismiss."
    ),
    collectors=("transcript-findings",),
    slot="triage",
    every="mon@09:00",
    output="entity:PATTERN",
    answer_type="PATTERN",
    status="active",
)
