import contextlib
import os
import threading
from collections.abc import Callable

from brigade.dashboard.answer_addon_lines import answer_addon_lines
from brigade.system.line_receiver import LineReceiver

READY_LINE = '{"awawa": "2.7.0"}'


class PipedChildDouble:
    def __init__(self, answer: Callable[[dict], dict], ready_line: str | None = READY_LINE, failure: str = ""):
        self.failure = failure
        child_input, self.input = os.pipe()
        self.output, child_output = os.pipe()
        self.writer = os.fdopen(self.input, "w", encoding="utf-8")
        self.receiver = LineReceiver(os.fdopen(self.output, "r", encoding="utf-8"))
        self.stopped = False
        self.serving = threading.Thread(
            target=self._serve,
            args=(os.fdopen(child_input, "r", encoding="utf-8"), os.fdopen(child_output, "w", encoding="utf-8")),
            kwargs={"answer": answer, "ready_line": ready_line},
            daemon=True,
        )
        self.serving.start()

    @staticmethod
    def _serve(reader, writer, answer, ready_line) -> None:
        with reader, writer, contextlib.suppress(SystemExit):
            if ready_line is None:
                return
            writer.write(f"{ready_line}\n")
            writer.flush()
            answer_addon_lines(reader, writer, answer)

    def send(self, line: str) -> None:
        self.writer.write(line)
        self.writer.flush()

    def receive(self, timeout_s: float) -> str | None:
        return self.receiver.receive(timeout_s)

    def is_running(self) -> bool:
        return not self.stopped and not self.receiver.has_ended() and self.serving.is_alive()

    def describe_failure(self) -> str:
        return self.failure

    def stop(self) -> None:
        self.stopped = True
        self.writer.close()

    def die(self) -> None:
        self.writer.close()
        self.serving.join()


class ChildStarterDouble:
    def __init__(self, create_child: Callable[[], PipedChildDouble]):
        self.create_child = create_child
        self.children: list[PipedChildDouble] = []

    def start(self) -> PipedChildDouble:
        child = self.create_child()
        self.children.append(child)
        return child


def answer_with_the_message(message: dict) -> dict:
    return {"document": {"asked": message}}
