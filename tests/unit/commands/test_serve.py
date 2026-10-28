import argparse
import contextlib
import io
import unittest

from brigade.commands.serve import COMMAND, serve
from tests.unit.create_test_runtime import create_test_runtime

SIGNALLED = True


def poll_twice_then_answer_signalled(poll, interval_s: float) -> bool:
    poll()
    poll()
    return SIGNALLED


class ServeTest(unittest.TestCase):
    def test_should_print_the_url_it_serves_until_a_stop_signal(self):
        # Arrange
        request = argparse.Namespace(port=0)
        runtime = create_test_runtime(poll_until_signalled=poll_twice_then_answer_signalled)

        # Act
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            document = serve(request, runtime)

        # Assert
        self.assertRegex(printed.getvalue(), r"\Ahttp://127\.0\.0\.1:[0-9]+/\n\Z")
        self.assertEqual(document, {"schema_version": 1, "url": printed.getvalue().strip()})


class ServeTextTest(unittest.TestCase):
    def test_should_say_which_url_it_stopped_serving(self):
        # Arrange
        document = {"schema_version": 1, "url": "http://127.0.0.1:8470/"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "stopped serving http://127.0.0.1:8470/")
