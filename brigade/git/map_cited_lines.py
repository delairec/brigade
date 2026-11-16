import re

HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,(\d+))? @@", re.MULTILINE)
ONE_LINE = "1"


def map_cited_lines(diff: str, start: int, end: int) -> tuple[int, int] | None:
    offset = 0
    for hunk in HUNK_HEADER.finditer(diff):
        old_start = int(hunk.group(1))
        old_count = int(hunk.group(2) or ONE_LINE)
        new_count = int(hunk.group(3) or ONE_LINE)
        if old_count == 0:
            if old_start < start:
                offset += new_count
            elif old_start < end:
                return None
            continue
        if old_start + old_count - 1 < start:
            offset += new_count - old_count
        elif old_start <= end:
            return None
    return (start + offset, end + offset)
