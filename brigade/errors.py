class BrigadeError(Exception):
    pass


class ToolFailure(BrigadeError):
    pass


class ToolNotFound(ToolFailure):
    pass


class CommandFailed(ToolFailure):
    def __init__(self, argv: tuple[str, ...], exit_code: int, stderr: str):
        super().__init__(f"{' '.join(argv)} exited {exit_code}: {stderr.strip()}")


class PullRequestCompareFailed(CommandFailed):
    def __init__(self, base: str, failure: CommandFailed):
        ToolFailure.__init__(self, str(failure))
        self.base = base


class EntityNotDefined(BrigadeError):
    pass


class TaskTypeMissing(BrigadeError):
    pass


class UsageError(BrigadeError):
    pass


class CorpusLintFailed(BrigadeError):
    pass


class InvalidPattern(BrigadeError):
    pass


class CannotWrite(BrigadeError):
    def __init__(self, path, error: OSError):
        reason = str(error) if error.strerror is None else error.strerror
        super().__init__(f"cannot write {path}: {reason}")


class StandingDown(Exception):
    pass
