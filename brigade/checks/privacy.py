from brigade.checks._read_pull_request import read_pull_request
from brigade.git.list_added_lines import AddedLine
from brigade.runtime import Runtime
from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION
from brigade.verify.check_privacy import PrivacyPatterns, check_privacy


def check(subject: dict, runtime: Runtime) -> dict:
    facts = read_pull_request(subject)
    patterns = PrivacyPatterns(private=tuple(facts["privacy"]["private"]), public=tuple(facts["privacy"]["public"]))
    added_lines = tuple(AddedLine(**added) for added in facts["added_lines"])
    return {"schema_version": CHECK_DOCUMENT_SCHEMA_VERSION, **check_privacy(patterns, added_lines)}
