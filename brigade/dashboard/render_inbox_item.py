from brigade.dashboard.render_fragment import render_fragment
from brigade.dashboard.render_report_fragment import render_report_fragment

ANSWER_KEY = "answer"
STUDY_ANSWER_KIND = "study-answer"


def render_inbox_item(document: dict) -> str:
    if ANSWER_KEY not in document:
        return render_fragment(document)
    answer = document[ANSWER_KEY]
    return render_report_fragment(
        {"report": {"kind": STUDY_ANSWER_KIND, "id": answer["id"], "fields": answer["fields"]}}
    )
