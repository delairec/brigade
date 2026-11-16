import io
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.test_clients.replay_recording import ReplayClock, replay_recording

NO_HOLD = ""
NO_PROGRESS = ""
NO_INTERVAL = "0"
NO_SOFT_LIMIT = "0"


class ClockDouble:
    def __init__(self, epochs: list[float]):
        self.epochs = epochs
        self.sleeps: list[float] = []

    def read_epoch(self) -> float:
        return self.epochs.pop(0) if len(self.epochs) > 1 else self.epochs[0]

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


class ReplayRecordingTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.recording = self.root / "builder.json"
        self.recording.write_text('{"type": "assistant"}\n{"outcome": "done"}\n')
        self.progress_file = self.root / "progress.md"
        self.output = io.StringIO()

    def tearDown(self):
        self.directory.cleanup()

    def replay(self, arguments: list[str], clock: ClockDouble) -> None:
        replay_recording(arguments, ReplayClock(read_epoch=clock.read_epoch, sleep=clock.sleep), self.output)

    def test_should_print_each_line_of_the_recording_then_wait_the_interval(self):
        # Arrange
        clock = ClockDouble([1791364980.0])
        arguments = [NO_HOLD, NO_PROGRESS, str(self.progress_file), str(self.recording), "1", NO_SOFT_LIMIT]

        # Act
        self.replay(arguments, clock)

        # Assert
        self.assertEqual(self.output.getvalue(), '{"type": "assistant"}\n{"outcome": "done"}\n')
        self.assertEqual(clock.sleeps, [1.0, 1.0])

    def test_should_append_its_progress_line_to_the_progress_file(self):
        # Arrange
        self.progress_file.write_text("step 0 done\n")
        clock = ClockDouble([1791364980.0])
        arguments = [NO_HOLD, "step 1 done", str(self.progress_file), str(self.recording), NO_INTERVAL, NO_SOFT_LIMIT]

        # Act
        self.replay(arguments, clock)

        # Assert
        self.assertEqual(self.progress_file.read_text(), "step 0 done\nstep 1 done\n")

    def test_should_write_no_progress_line_when_it_declares_none(self):
        # Arrange
        clock = ClockDouble([1791364980.0])
        arguments = [NO_HOLD, NO_PROGRESS, str(self.progress_file), str(self.recording), NO_INTERVAL, NO_SOFT_LIMIT]

        # Act
        self.replay(arguments, clock)

        # Assert
        self.assertFalse(self.progress_file.exists())

    def test_should_hold_while_its_hold_file_stands(self):
        # Arrange
        hold = self.root / "hold"
        hold.write_text("")
        clock = ClockDouble([1791364980.0])
        clock.sleep = lambda seconds: (clock.sleeps.append(seconds), hold.unlink(missing_ok=True))
        arguments = [str(hold), NO_PROGRESS, str(self.progress_file), str(self.recording), NO_INTERVAL, NO_SOFT_LIMIT]

        # Act
        self.replay(arguments, clock)

        # Assert
        self.assertEqual(clock.sleeps, [0.05, 0.0, 0.0])
        self.assertEqual(self.output.getvalue(), '{"type": "assistant"}\n{"outcome": "done"}\n')

    def test_should_print_nothing_before_its_soft_limit_has_passed(self):
        # Arrange
        clock = ClockDouble([1791364978.0, 1791364979.0, 1791364980.0])
        arguments = [NO_HOLD, NO_PROGRESS, str(self.progress_file), str(self.recording), NO_INTERVAL, "1791364980"]

        # Act
        self.replay(arguments, clock)

        # Assert
        self.assertEqual(clock.sleeps, [0.1, 0.1, 0.0, 0.0])
