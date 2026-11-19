import io
import os
import unittest

from brigade.system.line_receiver import LineReceiver

SHORT_WAIT_S = 0.05
LONG_WAIT_S = 5.0


def open_pipe(test_case: unittest.TestCase):
    reading, writing = os.pipe()
    reader = os.fdopen(reading, "r", encoding="utf-8")
    writer = os.fdopen(writing, "w", encoding="utf-8")
    test_case.addCleanup(reader.close)
    test_case.addCleanup(writer.close)
    return reader, writer


class LineReceiverTest(unittest.TestCase):
    def test_should_receive_each_line_written_without_its_newline(self):
        # Arrange
        receiver = LineReceiver(io.StringIO('{"awawa": "2.7.0"}\n{"document": {}}\n'))

        # Act
        lines = (receiver.receive(LONG_WAIT_S), receiver.receive(LONG_WAIT_S))

        # Assert
        self.assertEqual(lines, ('{"awawa": "2.7.0"}', '{"document": {}}'))

    def test_should_receive_nothing_once_the_stream_ends(self):
        # Arrange
        receiver = LineReceiver(io.StringIO(""))

        # Act
        line = receiver.receive(LONG_WAIT_S)

        # Assert
        self.assertIsNone(line)

    def test_should_receive_nothing_when_no_line_comes_within_the_wait(self):
        # Arrange
        reader, writer = open_pipe(self)
        receiver = LineReceiver(reader)

        # Act
        line = receiver.receive(SHORT_WAIT_S)

        # Assert
        self.assertIsNone(line)
        writer.close()

    def test_should_tell_the_stream_ended_once_its_end_is_received(self):
        # Arrange
        receiver = LineReceiver(io.StringIO(""))
        receiver.receive(LONG_WAIT_S)

        # Act
        ended = receiver.has_ended()

        # Assert
        self.assertTrue(ended)

    def test_should_tell_an_open_stream_has_not_ended(self):
        # Arrange
        reader, writer = open_pipe(self)
        receiver = LineReceiver(reader)

        # Act
        ended = receiver.has_ended()

        # Assert
        self.assertFalse(ended)
        writer.close()
