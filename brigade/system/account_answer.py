from dataclasses import dataclass


@dataclass(frozen=True)
class AccountAnswer:
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "AccountAnswer":
        return cls(login=document["login"])
