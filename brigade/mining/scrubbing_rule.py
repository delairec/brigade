import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ScrubbingRule:
    pattern: re.Pattern
    marker: str
    public: tuple[re.Pattern, ...]

    def scrub(self, text: str) -> str:
        return self.pattern.sub(self._replace, text)

    def _replace(self, found: re.Match) -> str:
        if any(public.fullmatch(found[0]) for public in self.public):
            return found[0]
        return self.marker
