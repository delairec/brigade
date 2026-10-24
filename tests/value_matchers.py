import re


class PatternMatcher:
    def __init__(self, pattern: str):
        self.pattern = pattern

    def __eq__(self, text: object) -> bool:
        return isinstance(text, str) and re.fullmatch(self.pattern, text) is not None

    def __repr__(self) -> str:
        return f"PatternMatcher({self.pattern!r})"


class DurationUnderMatcher:
    def __init__(self, limit_ms: int):
        self.limit_ms = limit_ms

    def __eq__(self, duration_ms: object) -> bool:
        return isinstance(duration_ms, int) and 0 <= duration_ms < self.limit_ms

    def __repr__(self) -> str:
        return f"DurationUnderMatcher({self.limit_ms})"
