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
            " that signal, and an ACTION, wave, constraint, order or dismiss. The document of inbox-families"
            " names each PATTERN the operational corpus holds with its TITLE: a family whose subject one of them"
            " covers, ratified or not, adds its signals to that PATTERN, in a PATTERN entity of its name holding"
            " one EVIDENCE per signal and no other field, and no new PATTERN is proposed on that subject."
        ),
        collectors=("inbox-families",),
        slot="triage",
        every=ONCE_A_DAY,
        output="entity:PATTERN",
        answer_type="PATTERN",
        status="active",
    )
