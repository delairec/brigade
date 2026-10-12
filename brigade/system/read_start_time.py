END_OF_PROCESS_NAME = ")"
START_TIME_AFTER_PROCESS_NAME = 19


def read_start_time(stat: str) -> int:
    fields = stat[stat.rindex(END_OF_PROCESS_NAME) + 1 :].split()
    return int(fields[START_TIME_AFTER_PROCESS_NAME])
