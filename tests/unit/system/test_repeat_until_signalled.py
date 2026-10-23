import signal
import unittest
from collections.abc import Callable
from functools import partial

from brigade.system.repeat_until_signalled import repeat_until_signalled
from tests.unit.system.signal_itself import signal_itself

SHORT_INTERVAL_S = 0.01


def do_nothing() -> None:
    return None


class ScriptedActionDouble:
    def __init__(self, steps: list[Callable[[], None]]):
        self.steps = iter(steps)

    def __call__(self) -> None:
        next(self.steps)()


class RepeatUntilSignalledTest(unittest.TestCase):
    def setUp(self):
        self.handlers_before = (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT))

    def tearDown(self):
        signal.signal(signal.SIGTERM, self.handlers_before[0])
        signal.signal(signal.SIGINT, self.handlers_before[1])

    def test_should_count_the_repetitions_up_to_the_one_under_way_when_the_signal_came(self):
        # Arrange
        action = ScriptedActionDouble([do_nothing, do_nothing, partial(signal_itself, signal.SIGTERM)])

        # Act
        repetitions = repeat_until_signalled(action, SHORT_INTERVAL_S)

        # Assert
        self.assertEqual(repetitions, 3)
