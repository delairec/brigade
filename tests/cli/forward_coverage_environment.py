import os

COVERAGE_VARIABLE = "COVERAGE_PROCESS_CONFIG"


def forward_coverage_environment() -> dict:
    if COVERAGE_VARIABLE not in os.environ:
        return {}
    return {COVERAGE_VARIABLE: os.environ[COVERAGE_VARIABLE]}
