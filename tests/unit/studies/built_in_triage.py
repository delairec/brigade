from brigade.studies.convert_study import Study

BUILT_IN_TRIAGE = Study(
    name="triage",
    project=None,
    question=(
        "Group the families of new signals into patterns: one PATTERN entity per structural problem,"
        " with its TITLE, STATUS new, one EVIDENCE per signal it groups opening on the fingerprint of"
        " that signal, and an ACTION, wave, constraint, order or dismiss."
    ),
    collectors=("inbox-families",),
    slot="triage",
    every="24h",
    output="entity:PATTERN",
    answer_type="PATTERN",
    status="active",
)
