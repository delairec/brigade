import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.serve import COMMAND, serve
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.dashboard.addon_child_double import PipedChildDouble, answer_with_the_message

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


class ServeWithAProjectHoldingACorpusTest(unittest.TestCase):
    def test_should_start_the_awawa_addon_and_stop_it_once_signalled(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        paths = create_test_paths(Path(root.name))
        paths.config_root.mkdir(parents=True)
        paths.schema_file.write_text("SCHEMA PROJECT\n")
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(
                    stdout=json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
                ),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(
                    stdout=json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})
                ),
                ("awawa", "status", "--json", "/srv/app"): ProcessAnswer(stdout='{"summary": {"files": 2}}'),
            }
        )
        children = []

        def start_child(request):
            children.append(PipedChildDouble(answer_with_the_message))
            return children[-1]

        runtime = create_test_runtime(
            paths,
            run_process=runner.run,
            start_piped_process=start_child,
            poll_until_signalled=poll_twice_then_answer_signalled,
        )

        # Act
        with contextlib.redirect_stdout(io.StringIO()):
            serve(argparse.Namespace(port=0), runtime)

        # Assert
        self.assertEqual(len(children), 1)
        self.assertFalse(children[0].is_running())


class ServeTextTest(unittest.TestCase):
    def test_should_say_which_url_it_stopped_serving(self):
        # Arrange
        document = {"schema_version": 1, "url": "http://127.0.0.1:8470/"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "stopped serving http://127.0.0.1:8470/")
