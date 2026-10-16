from brigade.errors import BrigadeError

INBOX_OUTPUT = "inbox"


def refuse_inbox_output(output: str) -> None:
    if output == INBOX_OUTPUT:
        raise BrigadeError("the output inbox is refused: the inbox has no store until @TASK.B22")
