class BrigadeError(Exception):
    pass


class ToolFailure(BrigadeError):
    pass


class ToolNotFound(ToolFailure):
    pass


class EntityNotDefined(BrigadeError):
    pass


class UsageError(BrigadeError):
    pass


class CannotWrite(BrigadeError):
    def __init__(self, path, error: OSError):
        reason = str(error) if error.strerror is None else error.strerror
        super().__init__(f"cannot write {path}: {reason}")


class StandingDown(Exception):
    pass
