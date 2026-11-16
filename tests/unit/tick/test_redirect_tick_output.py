import os
import tempfile
import unittest
from pathlib import Path

from brigade.tick.redirect_tick_output import redirect_tick_output

STDOUT = 1
STDERR = 2


def _redirect_then_write(log_file: Path, descriptor: int, text: str) -> None:
    redirect_tick_output(log_file)
    os.write(descriptor, text.encode("utf-8"))


class RedirectTickOutputTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.captured_stdout = self.root / "stdout"
        self.saved_stdout = os.dup(STDOUT)
        self.saved_stderr = os.dup(STDERR)
        capture = os.open(self.captured_stdout, os.O_WRONLY | os.O_CREAT, 0o644)
        os.dup2(capture, STDOUT)
        os.close(capture)

    def tearDown(self):
        os.dup2(self.saved_stdout, STDOUT)
        os.dup2(self.saved_stderr, STDERR)
        os.close(self.saved_stdout)
        os.close(self.saved_stderr)

    def test_should_append_what_the_tick_writes_on_stderr_to_its_log_file(self):
        # Arrange
        log_file = self.root / "tick.log"
        log_file.write_text("tick of 09:00 stood down\n", encoding="utf-8")

        # Act
        _redirect_then_write(log_file, STDERR, "tick of 09:05 failed\n")

        # Assert
        self.assertEqual(log_file.read_text(encoding="utf-8"), "tick of 09:00 stood down\ntick of 09:05 failed\n")

    def test_should_create_the_directory_of_its_log_file(self):
        # Arrange
        log_file = self.root / "state" / "logs" / "tick.log"

        # Act
        _redirect_then_write(log_file, STDERR, "tick of 09:05 failed\n")

        # Assert
        self.assertEqual(log_file.read_text(encoding="utf-8"), "tick of 09:05 failed\n")

    def test_should_discard_what_the_tick_writes_on_stdout(self):
        # Arrange
        log_file = self.root / "tick.log"

        # Act
        _redirect_then_write(log_file, STDOUT, '{"mode": "once"}\n')

        # Assert
        self.assertEqual(self.captured_stdout.read_text(encoding="utf-8"), "")
        self.assertEqual(log_file.read_text(encoding="utf-8"), "")
