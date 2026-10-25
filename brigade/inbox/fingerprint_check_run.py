from brigade.collecting.name_check_run_subject import name_check_run_subject

FINGERPRINT_PREFIX = "cr"


def fingerprint_check_run(project: str, check_run: dict) -> str:
    return f"{FINGERPRINT_PREFIX}:{project}:{name_check_run_subject(check_run)}:{check_run['name']}:{check_run['head']}"
