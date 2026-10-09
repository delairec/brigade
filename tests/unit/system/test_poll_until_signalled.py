import os
import signal
import unittest

from brigade.system.poll_until_signalled import poll_until_signalled

SHORT_INTERVAL_S = 0.01
NEVER = 0


class Poll:
    def __init__(self, done_at_call: int, signal_at_call: int = NEVER, stop_signal: int = signal.SIGTERM):
        self.done_at_call = done_at_call
        self.signal_at_call = signal_at_call
        self.stop_signal = stop_signal
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        if self.calls == self.signal_at_call:
            os.kill(os.getpid(), self.stop_signal)
        return self.calls == self.done_at_call


class PollUntilSignalledTest(unittest.TestCase):
    def setUp(self):
        self.handlers_before = (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT))

    def tearDown(self):
        signal.signal(signal.SIGTERM, self.handlers_before[0])
        signal.signal(signal.SIGINT, self.handlers_before[1])

    def test_should_stop_once_the_poll_answers_done_and_answer_that_no_signal_stopped_it(self):
        # Arrange
        poll = Poll(done_at_call=3)

        # Act
        signalled = poll_until_signalled(poll, SHORT_INTERVAL_S)

        # Assert
        self.assertEqual((signalled, poll.calls), (False, 3))

    def test_should_finish_the_poll_under_way_and_stop_on_a_signal(self):
        rows = [("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT)]
        for name, stop_signal in rows:
            with self.subTest(signal=name):
                # Arrange
                poll = Poll(done_at_call=5, signal_at_call=2, stop_signal=stop_signal)

                # Act
                signalled = poll_until_signalled(poll, SHORT_INTERVAL_S)

                # Assert
                self.assertEqual((signalled, poll.calls), (True, 2))

    def test_should_restore_the_signal_handlers_it_replaced(self):
        # Arrange
        poll = Poll(done_at_call=2, signal_at_call=1)

        # Act
        poll_until_signalled(poll, SHORT_INTERVAL_S)

        # Assert
        self.assertEqual((signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT)), self.handlers_before)
