SUCCEEDED_OUTCOME = "exited"
SUCCEEDED_EXIT_CODE = 0


def is_failed_record(record: dict) -> bool:
    return not (record["outcome"] == SUCCEEDED_OUTCOME and record["exit"] == SUCCEEDED_EXIT_CODE)
