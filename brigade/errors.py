class BrigadeError(Exception):
    pass


class ToolFailure(BrigadeError):
    pass


class ToolNotFound(ToolFailure):
    pass


class UsageError(BrigadeError):
    pass


class StandingDown(Exception):
    pass
