import re
from dataclasses import dataclass

from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.verify.check_privacy import BUILT_IN_PATTERNS
from brigade.verify.read_privacy_patterns import read_privacy_patterns

PRIVATE_MARKER = "[private]"
NO_PUBLIC_PATTERN = ()


@dataclass(frozen=True)
class _ScrubbingRule:
    pattern: re.Pattern
    marker: str
    public: tuple[re.Pattern, ...]

    def replace(self, found: re.Match) -> str:
        if any(public.fullmatch(found[0]) for public in self.public):
            return found[0]
        return self.marker


def _list_rules(runtime: Runtime) -> list[_ScrubbingRule]:
    rules = [
        _ScrubbingRule(pattern, f"[{description.partition(' ')[2]}]", NO_PUBLIC_PATTERN)
        for pattern, description in BUILT_IN_PATTERNS
    ]
    for project in read_projects(runtime):
        patterns = read_privacy_patterns(project)
        public = tuple(re.compile(pattern) for pattern in patterns.public)
        rules.extend(_ScrubbingRule(re.compile(pattern), PRIVATE_MARKER, public) for pattern in patterns.private)
    return rules


def _scrub(value, rules: list[_ScrubbingRule]):
    if isinstance(value, dict):
        return {key: _scrub(item, rules) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item, rules) for item in value]
    if not isinstance(value, str):
        return value
    for rule in rules:
        value = rule.pattern.sub(rule.replace, value)
    return value


def scrub_document(document: dict, runtime: Runtime) -> dict:
    return _scrub(document, _list_rules(runtime))
