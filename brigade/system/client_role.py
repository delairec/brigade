from dataclasses import dataclass


@dataclass(frozen=True)
class ClientRole:
    name: str
    package: str
    package_file: str
    capabilities: tuple[str, ...]
    reasoning: str
    budget: int

    @classmethod
    def from_document(cls, document: dict) -> "ClientRole":
        return cls(
            name=document["name"],
            package=document["package"],
            package_file=document["package_file"],
            capabilities=tuple(document["capabilities"]),
            reasoning=document["reasoning"],
            budget=document["budget"],
        )

    def to_document(self) -> dict:
        return {
            "name": self.name,
            "package": self.package,
            "package_file": self.package_file,
            "capabilities": list(self.capabilities),
            "reasoning": self.reasoning,
            "budget": self.budget,
        }
