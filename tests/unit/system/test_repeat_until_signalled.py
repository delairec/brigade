import os
import signal
import unittest

from brigade.system.repeat_until_signalled import repeat_until_signalled

SHORT_INTERVAL_S = 0.01


class SignallingAction:
    def __init__(self, stop_signal: int, signalled_at_call: int):
        self.stop_signal = stop_signal
        self.signalled_at_call = signalled_at_call
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1
        if self.calls == self.signalled_at_call:
            os.kill(os.getpid(), self.stop_signal)


class RepeatUntilSignalledTest(unittest.TestCase):
    def setUp(self):
        self.handlers_before = (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT))

    def tearDown(self):
        signal.signal(signal.SIGTERM, self.handlers_before[0])
        signal.signal(signal.SIGINT, self.handlers_before[1])

    def test_should_finish_the_action_under_way_and_stop_on_a_signal(self):
        rows = [("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT)]
        for name, stop_signal in rows:
            with self.subTest(signal=name):
                # Arrange
                action = SignallingAction(stop_signal, signalled_at_call=3)

                # Act
                repetitions = repeat_until_signalled(action, SHORT_INTERVAL_S)

                # Assert
                self.assertEqual((repetitions, action.calls), (3, 3))

    def test_should_restore_the_signal_handlers_it_replaced(self):
        # Arrange
        action = SignallingAction(signal.SIGTERM, signalled_at_call=1)

        # Act
        repeat_until_signalled(action, SHORT_INTERVAL_S)

        # Assert
        self.assertEqual((signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT)), self.handlers_before)
