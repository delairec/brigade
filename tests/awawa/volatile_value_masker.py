import re

PLACEHOLDER = re.compile(r"<tmp:(\d+)>")
INSTANT_PLACEHOLDER = re.compile(r"<instant:(\d+)>")
VOLATILE_PLACEHOLDER = re.compile(r"<(?:tmp|instant):\d+>")
NAME_IN_TEMPORARY_ROOT = r"/[^/\s\"'`:;,()\[\]{}<>]+"
UTC_INSTANT = r"(?P<instant>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)"


class VolatileValueMasker:
    def __init__(self, temporary_roots: list[str], known: dict[str, str] | None = None):
        alternatives = [re.escape(root) + NAME_IN_TEMPORARY_ROOT for root in temporary_roots]
        self._volatile = re.compile("|".join([UTC_INSTANT, *alternatives]))
        self._values = dict(known or {})
        self._placeholders = {value: placeholder for placeholder, value in self._values.items()}

    def _replace_value(self, match: re.Match) -> str:
        value = match.group(0)
        if value not in self._placeholders:
            kind = "instant" if match.group("instant") is not None else "tmp"
            placeholder = f"<{kind}:{len(self._values)}>"
            self._values[placeholder] = value
            self._placeholders[value] = placeholder
        return self._placeholders[value]

    def mask(self, text: str) -> str:
        return self._volatile.sub(self._replace_value, text)

    def unmask(self, text: str) -> str:
        return VOLATILE_PLACEHOLDER.sub(lambda match: self._values[match.group(0)], text)
