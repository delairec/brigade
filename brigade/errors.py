class BrigadeError(Exception):
    pass


class ToolFailure(BrigadeError):
    pass


class ToolNotFound(ToolFailure):
    pass
