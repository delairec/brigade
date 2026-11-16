OK = "ok"
FAILED = "fail"


def judge_findings(name: str, findings: list[str]) -> dict:
    return {"name": name, "result": FAILED if findings else OK, "findings": findings}
