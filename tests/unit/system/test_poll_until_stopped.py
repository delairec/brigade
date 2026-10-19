import unittest

from brigade.system.poll_until_stopped import poll_until_stopped

INTERVAL_S = 5.0


class StopSignalsDouble:
    def __init__(self, *, stop_while_waiting: bool):
        self.stop_while_waiting = stop_while_waiting
        self.stopped = False
        self.waits = []

    def received(self) -> bool:
        return self.stopped

    def wait(self, interval_s: float) -> None:
        self.waits.append(interval_s)
        self.stopped = self.stop_while_waiting


class ScriptedPoller:
    def __init__(self, answers: list[bool], signals: StopSignalsDouble | None = None):
        self.answers = answers
        self.signals = signals
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        if self.signals is not None:
            self.signals.stopped = True
        return self.answers.pop(0)


class PollUntilStoppedWithoutStopTest(unittest.TestCase):
    def test_should_wait_between_polls_until_the_poll_answers_done(self):
        # Arrange
        signals = StopSignalsDouble(stop_while_waiting=False)
        poller = ScriptedPoller([False, False, True])

        # Act
        stopped = poll_until_stopped(poller, INTERVAL_S, signals)

        # Assert
        self.assertEqual((stopped, poller.calls, signals.waits), (False, 3, [5.0, 5.0]))


class PollUntilStoppedOnAStopTest(unittest.TestCase):
    def test_should_finish_the_poll_under_way_and_stop_without_waiting(self):
        # Arrange
        signals = StopSignalsDouble(stop_while_waiting=False)
        poller = ScriptedPoller([True], signals)

        # Act
        stopped = poll_until_stopped(poller, INTERVAL_S, signals)

        # Assert
        self.assertEqual((stopped, poller.calls, signals.waits), (True, 1, []))

    def test_should_stop_without_polling_again_on_a_stop_received_while_waiting(self):
        # Arrange
        signals = StopSignalsDouble(stop_while_waiting=True)
        poller = ScriptedPoller([False])

        # Act
        stopped = poll_until_stopped(poller, INTERVAL_S, signals)

        # Assert
        self.assertEqual((stopped, poller.calls, signals.waits), (True, 1, [5.0]))
