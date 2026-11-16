from brigade.system.check_shapes import CHECK_DOCUMENT_SCHEMA_VERSION, FAILED, PASSED


def report_findings(name: str, findings: list[str]) -> dict:
    return {
        "schema_version": CHECK_DOCUMENT_SCHEMA_VERSION,
        "name": name,
        "verdict": FAILED if findings else PASSED,
        "findings": findings,
    }
