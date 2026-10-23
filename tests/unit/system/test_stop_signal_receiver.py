import os
import signal
import unittest

from brigade.system.stop_signal_receiver import StopRequested, StopSignalReceiver

STOP_SIGNALS = [("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT)]


def signal_itself(stop_signal: int) -> None:
    os.kill(os.getpid(), stop_signal)


def finish_a_write_while_signalled(receiver: StopSignalReceiver, written: list[str]) -> None:
    with receiver.holding():
        signal_itself(signal.SIGTERM)
        written.append("the whole write")


class StopSignalReceiverTestCase(unittest.TestCase):
    def setUp(self):
        self.handlers_before = (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT))
        self.addCleanup(signal.signal, signal.SIGINT, self.handlers_before[1])
        self.addCleanup(signal.signal, signal.SIGTERM, self.handlers_before[0])


class StopSignalReceivedOutsideTheWaitTest(StopSignalReceiverTestCase):
    def test_should_record_the_stop_and_raise_nothing(self):
        for name, stop_signal in STOP_SIGNALS:
            with self.subTest(signal=name):
                # Arrange
                receiver = StopSignalReceiver()

                # Act
                with receiver:
                    signal_itself(stop_signal)

                # Assert
                self.assertTrue(receiver.requested)

    def test_should_raise_on_entering_the_wait(self):
        # Arrange
        receiver = StopSignalReceiver()

        with receiver:
            signal_itself(signal.SIGTERM)

            # Act
            entering_the_wait = receiver.raising()

            # Assert
            with self.assertRaises(StopRequested), entering_the_wait:
                pass


class StopSignalReceivedWhileWaitingTest(StopSignalReceiverTestCase):
    def test_should_raise_where_the_wait_stands(self):
        for name, stop_signal in STOP_SIGNALS:
            with self.subTest(signal=name):
                # Arrange
                receiver = StopSignalReceiver()

                # Act
                with receiver, receiver.raising(), self.assertRaises(StopRequested):
                    signal_itself(stop_signal)

                # Assert
                self.assertTrue(receiver.requested)

    def test_should_raise_once_and_let_the_stop_under_way_finish(self):
        # Arrange
        receiver = StopSignalReceiver()

        with receiver, receiver.raising():
            with self.assertRaises(StopRequested):
                signal_itself(signal.SIGTERM)

            # Act
            signal_itself(signal.SIGINT)

        # Assert
        self.assertTrue(receiver.requested)


class StopSignalReceivedWhileHoldingTest(StopSignalReceiverTestCase):
    def test_should_raise_once_the_hold_ends_within_the_wait(self):
        # Arrange
        receiver = StopSignalReceiver()
        written = []

        # Act
        with receiver, receiver.raising(), self.assertRaises(StopRequested):
            finish_a_write_while_signalled(receiver, written)

        # Assert
        self.assertEqual(written, ["the whole write"])

    def test_should_raise_once_the_hold_ends_and_let_the_stop_under_way_finish(self):
        # Arrange
        receiver = StopSignalReceiver()
        written = []

        with receiver, receiver.raising():
            with self.assertRaises(StopRequested):
                finish_a_write_while_signalled(receiver, written)

            # Act
            signal_itself(signal.SIGINT)

        # Assert
        self.assertTrue(receiver.requested)

    def test_should_record_the_stop_and_raise_nothing_outside_the_wait(self):
        # Arrange
        receiver = StopSignalReceiver()
        written = []

        # Act
        with receiver:
            finish_a_write_while_signalled(receiver, written)

        # Assert
        self.assertEqual(written, ["the whole write"])
        self.assertEqual(receiver.requested, True)


class StopSignalReceiverLeftTest(StopSignalReceiverTestCase):
    def test_should_restore_the_signal_handlers_it_replaced(self):
        # Arrange
        receiver = StopSignalReceiver()

        # Act
        with receiver:
            pass

        # Assert
        self.assertEqual(signal.getsignal(signal.SIGTERM), self.handlers_before[0])
        self.assertEqual(signal.getsignal(signal.SIGINT), self.handlers_before[1])

    def test_should_start_with_no_stop_requested(self):
        # Act
        receiver = StopSignalReceiver()

        # Assert
        self.assertFalse(receiver.requested)
