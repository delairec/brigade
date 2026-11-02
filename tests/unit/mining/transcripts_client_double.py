from brigade.errors import BrigadeError


class TranscriptsClientDouble:
    def __init__(self, transcripts: dict):
        self.transcripts = transcripts
        self.worktrees = []

    def answer(self, operation: str, request: dict) -> dict:
        self.worktrees.append(request["worktree"])
        if request["session_id"] not in self.transcripts:
            raise BrigadeError(f"no transcript of session {request['session_id']}")
        return {"schema_version": 1, "messages": self.transcripts[request["session_id"]], "subagents": []}
