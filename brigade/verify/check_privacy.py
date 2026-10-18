import re

from brigade.git.list_added_lines import AddedLine
from brigade.verify.judge_findings import judge_findings

NAME = "privacy"
BUILT_IN_PATTERNS = (
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "an e-mail address"),
    (re.compile(r"/(?:home|Users)/[\w.-]+"), "a home path"),
)


def check_privacy(private_patterns: tuple[str, ...], added_lines: tuple[AddedLine, ...]) -> dict:
    patterns = (
        *BUILT_IN_PATTERNS,
        *((re.compile(pattern), f"the PRIVATE pattern {pattern}") for pattern in private_patterns),
    )
    return judge_findings(
        NAME,
        [
            f"{added.path}:{added.line}: {description}"
            for added in added_lines
            for pattern, description in patterns
            if pattern.search(added.text)
        ],
    )
