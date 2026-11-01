from dataclasses import dataclass

DOCUMENT_SCHEMA_VERSION = 1
ATTRIBUTION_KEY = "attribution"
EDIT_TOOLS_KEY = "edit_tools"
NO_EDIT_TOOL = ()
NO_ATTRIBUTION = ()


@dataclass(frozen=True)
class ProbeAnswer:
    client: str
    version_argv: tuple[str, ...] | None
    operations: tuple[str, ...]
    features: tuple[str, ...]
    models: dict
    attribution: tuple[str, ...] = NO_ATTRIBUTION
    edit_tools: tuple[str, ...] = NO_EDIT_TOOL

    @classmethod
    def from_document(cls, document: dict) -> "ProbeAnswer":
        version_argv = document["version_argv"]
        return cls(
            client=document["client"],
            version_argv=None if version_argv is None else tuple(version_argv),
            operations=tuple(document["operations"]),
            features=tuple(document["features"]),
            models=document["models"],
            attribution=tuple(document.get(ATTRIBUTION_KEY, NO_ATTRIBUTION)),
            edit_tools=tuple(document.get(EDIT_TOOLS_KEY, NO_EDIT_TOOL)),
        )

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "client": self.client,
            "version_argv": None if self.version_argv is None else list(self.version_argv),
            "operations": list(self.operations),
            "features": list(self.features),
            "models": self.models,
            **({ATTRIBUTION_KEY: list(self.attribution)} if self.attribution else {}),
            **({EDIT_TOOLS_KEY: list(self.edit_tools)} if self.edit_tools else {}),
        }
