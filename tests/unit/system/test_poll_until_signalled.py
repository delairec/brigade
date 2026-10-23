import os
import signal
import unittest
from collections.abc import Callable

from brigade.system.poll_until_signalled import poll_until_signalled

SHORT_INTERVAL_S = 0.01


def answer_not_done() -> bool:
    return False


def answer_done() -> bool:
    return True


def create_signalling_answer(stop_signal: int) -> Callable[[], bool]:
    def signal_itself_and_answer_not_done() -> bool:
        os.kill(os.getpid(), stop_signal)
        return False

    return signal_itself_and_answer_not_done


class ScriptedPollerDouble:
    def __init__(self, answers: list[Callable[[], bool]]):
        self.answers = iter(answers)
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        return next(self.answers)()


class PollUntilSignalledTest(unittest.TestCase):
    def setUp(self):
        self.handlers_before = (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT))

    def tearDown(self):
        signal.signal(signal.SIGTERM, self.handlers_before[0])
        signal.signal(signal.SIGINT, self.handlers_before[1])

    def test_should_stop_once_the_poll_answers_done_and_answer_that_no_signal_stopped_it(self):
        # Arrange
        poller = ScriptedPollerDouble([answer_not_done, answer_not_done, answer_done])

        # Act
        signalled = poll_until_signalled(poller, SHORT_INTERVAL_S)

        # Assert
        self.assertEqual((signalled, poller.calls), (False, 3))

    def test_should_finish_the_poll_under_way_and_stop_on_a_signal(self):
        # Arrange
        rows = [("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT)]
        for name, stop_signal in rows:
            with self.subTest(signal=name):
                # Arrange
                poller = ScriptedPollerDouble([answer_not_done, create_signalling_answer(stop_signal), answer_done])

                # Act
                signalled = poll_until_signalled(poller, SHORT_INTERVAL_S)

                # Assert
                self.assertEqual((signalled, poller.calls), (True, 2))

    def test_should_restore_the_signal_handlers_it_replaced(self):
        # Arrange
        poller = ScriptedPollerDouble([create_signalling_answer(signal.SIGTERM)])

        # Act
        poll_until_signalled(poller, SHORT_INTERVAL_S)

        # Assert
        self.assertEqual((signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT)), self.handlers_before)
