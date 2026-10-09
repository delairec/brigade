from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class ForgeAccountUnavailable:
    name: ClassVar[str] = "forge_account_unavailable"
    login: str
    key: str

    @classmethod
    def from_document(cls, document: dict) -> "ForgeAccountUnavailable":
        return cls(login=document["login"], key=document["key"])

    def to_document(self) -> dict:
        return {"login": self.login, "key": self.key}
