class ClientDouble:
    def __init__(self, name: str, version_argv: list[str] | None):
        self.name = name
        self.version_argv = version_argv

    def answer(self, operation: str, request: dict) -> dict:
        return {
            "schema_version": 1,
            "client": self.name,
            "version_argv": self.version_argv,
            "operations": ["probe", "launch", "result"],
            "features": [],
            "models": {},
        }


def create_built_in_clients() -> dict:
    return {
        ("client", "claude-code"): ClientDouble("claude-code", ["claude", "--version"]),
        ("client", "vibe"): ClientDouble("vibe", ["vibe", "--version"]),
    }
