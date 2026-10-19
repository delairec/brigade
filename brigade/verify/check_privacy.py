import re
from dataclasses import dataclass

from brigade.git.list_added_lines import AddedLine
from brigade.verify.judge_findings import judge_findings

NAME = "privacy"
BUILT_IN_PATTERNS = (
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "an e-mail address"),
    (re.compile(r"/(?:home|Users)/[\w.-]+"), "a home path"),
)


@dataclass(frozen=True)
class PrivacyPatterns:
    private: tuple[str, ...]
    public: tuple[str, ...]


def check_privacy(patterns: PrivacyPatterns, added_lines: tuple[AddedLine, ...]) -> dict:
    refused = (
        *BUILT_IN_PATTERNS,
        *((re.compile(pattern), f"the PRIVATE pattern {pattern}") for pattern in patterns.private),
    )
    allowed = tuple(re.compile(pattern) for pattern in patterns.public)
    return judge_findings(
        NAME,
        [
            f"{added.path}:{added.line}: {description}"
            for added in added_lines
            for pattern, description in refused
            if any(not any(public.fullmatch(found[0]) for public in allowed) for found in pattern.finditer(added.text))
        ],
    )
