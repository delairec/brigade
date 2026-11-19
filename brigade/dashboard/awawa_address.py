from dataclasses import dataclass
from urllib.parse import quote, urlencode

TAB = "#awawa/"
QUERY_SEPARATOR = "?"


@dataclass(frozen=True)
class AwawaAddress:
    project: str
    parameters: tuple[tuple[str, str], ...] = ()

    def read(self, name: str) -> str | None:
        return next(iter(self.read_all(name)), None)

    def read_all(self, name: str) -> tuple[str, ...]:
        return tuple(value for written, value in self.parameters if written == name)

    def setting(self, name: str, value: str) -> "AwawaAddress":
        return AwawaAddress(self.project, (*self.removing(name).parameters, (name, value)))

    def adding(self, name: str, value: str) -> "AwawaAddress":
        return AwawaAddress(self.project, (*self.parameters, (name, value)))

    def removing(self, name: str, value: str | None = None) -> "AwawaAddress":
        kept = tuple(
            (written, held) for written, held in self.parameters if written != name or value not in (None, held)
        )
        return AwawaAddress(self.project, kept)

    def link(self) -> str:
        tab = f"{TAB}{quote(self.project, safe='')}"
        return f"{tab}{QUERY_SEPARATOR}{urlencode(self.parameters)}" if self.parameters else tab
