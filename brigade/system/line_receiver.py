import queue
import threading
from typing import TextIO

END_OF_STREAM = None


class LineReceiver:
    def __init__(self, stream: TextIO):
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.ended = threading.Event()
        threading.Thread(target=self._read, args=(stream,), daemon=True).start()

    def _read(self, stream: TextIO) -> None:
        with stream:
            for line in stream:
                self.lines.put(line.removesuffix("\n"))
        self.ended.set()
        self.lines.put(END_OF_STREAM)

    def has_ended(self) -> bool:
        return self.ended.is_set()

    def receive(self, timeout_s: float) -> str | None:
        try:
            return self.lines.get(timeout=timeout_s)
        except queue.Empty:
            return None
