import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.errors import ToolNotFound
from brigade.system.spawn_process import SpawnRequest, _feed, spawn_process


class SpawnProcessTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.stdout_path = Path(self.root.name) / "stdout.log"
        self.stderr_path = Path(self.root.name) / "stderr.log"

    def tearDown(self):
        self.root.cleanup()

    def make_request(self, **overrides) -> SpawnRequest:
        defaults = {
            "argv": ("echo", "hello"),
            "cwd": "/",
            "environment": {},
            "stdin": None,
            "stdout": self.stdout_path,
            "stderr": self.stderr_path,
        }
        return SpawnRequest(**{**defaults, **overrides})

    def test_should_spawn_a_process_and_return_it(self):
        # Act
        process = spawn_process(self.make_request())
        process.wait()

        # Assert
        self.assertEqual(process.returncode, 0)
        self.assertEqual(self.stdout_path.read_text().strip(), "hello")

    def test_should_feed_the_stdin_to_the_process(self):
        # Act
        process = spawn_process(self.make_request(argv=("cat",), stdin="piped input\n"))
        process.wait()

        # Assert
        self.assertEqual(process.returncode, 0)
        self.assertEqual(self.stdout_path.read_text(), "piped input\n")

    def test_should_raise_tool_not_found_when_the_executable_is_absent(self):
        # Act
        with self.assertRaises(ToolNotFound) as raised:
            spawn_process(self.make_request(argv=("nonexistent-command-xyz",)))

        # Assert
        self.assertEqual(str(raised.exception), "nonexistent-command-xyz not on PATH")

    def test_should_handle_a_broken_pipe_when_feeding_stdin(self):
        # Arrange
        request = self.make_request(argv=("true",), stdin="ignored")

        # Act
        with mock.patch("brigade.system.spawn_process._feed") as feed:
            process = spawn_process(request)
            process.wait()

        # Assert
        feed.assert_called_once()


class FeedTest(unittest.TestCase):
    def test_should_write_the_data_and_close_the_pipe(self):
        # Arrange
        pipe = mock.Mock()

        # Act
        _feed(pipe, b"data")

        # Assert
        pipe.write.assert_called_once_with(b"data")
        pipe.close.assert_called_once()

    def test_should_ignore_a_broken_pipe_on_write(self):
        # Arrange
        pipe = mock.Mock()
        pipe.write.side_effect = BrokenPipeError

        # Act
        _feed(pipe, b"data")

        # Assert
        pipe.close.assert_called_once()

    def test_should_ignore_a_broken_pipe_on_close(self):
        # Arrange
        pipe = mock.Mock()
        pipe.close.side_effect = BrokenPipeError

        # Act
        _feed(pipe, b"data")

        # Assert
        pipe.write.assert_called_once_with(b"data")
