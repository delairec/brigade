DRAFT_COLLECTOR = "draft"


def read_draft(subject: dict) -> dict:
    return subject["collected"][DRAFT_COLLECTOR]
