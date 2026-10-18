PASSED = "pass"
FAILED = "fail"


def judge_findings(name: str, findings: list[str]) -> dict:
    return {"name": name, "verdict": FAILED if findings else PASSED, "findings": findings}
