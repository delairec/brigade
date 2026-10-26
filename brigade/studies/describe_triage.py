from brigade.studies.convert_study import Study

NAME = "triage"
ONCE_A_DAY = "24h"


def describe_triage() -> Study:
    return Study(
        name=NAME,
        project=None,
        question=(
            "Group the families of new signals into patterns: one PATTERN entity per structural problem,"
            " with its TITLE, STATUS new, one EVIDENCE per signal it groups opening on the fingerprint of"
            " that signal, and an ACTION, wave, constraint, order or dismiss."
        ),
        collectors=("inbox-families",),
        slot="triage",
        every=ONCE_A_DAY,
        output="entity:PATTERN",
        answer_type="PATTERN",
        status="active",
    )
