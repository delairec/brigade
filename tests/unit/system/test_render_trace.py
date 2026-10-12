import unittest

from brigade.system.process_trace import ProcessTrace
from brigade.system.render_trace import render_trace


class RenderTraceTest(unittest.TestCase):
    def test_should_render_the_command_and_how_it_ended(self):
        rows = [
            ("exited", ProcessTrace(("git", "--version"), "/", "exited", 0, 3), "ran git --version, exit 0 in 3 ms"),
            (
                "timed out",
                ProcessTrace(("sleep", "30"), "/", "timed_out", None, 100),
                "ran sleep 30, timed out after 100 ms",
            ),
            ("not found", ProcessTrace(("awawa", "lint"), "/", "not_found", None, 1), "ran awawa lint, not on PATH"),
            (
                "no working directory",
                ProcessTrace(("awawa", "show"), "/srv/absent", "no_working_directory", None, 1),
                "ran awawa show, no working directory /srv/absent",
            ),
            ("cut", ProcessTrace(("claude", "-p"), "/", "cut", None, 400), "ran claude -p, cut after 400 ms"),
            (
                "stopped",
                ProcessTrace(("claude", "-p"), "/", "stopped", None, 400),
                "ran claude -p, stopped after 400 ms",
            ),
            (
                "spawned",
                ProcessTrace(("brigade", "run"), "/", "spawned", None, None, pid=4242),
                "ran brigade run, spawned pid 4242",
            ),
            (
                "quoted",
                ProcessTrace(("git", "commit", "-m", "two words"), "/", "exited", 0, 9),
                "ran git commit -m 'two words', exit 0 in 9 ms",
            ),
        ]
        for case, trace, expected in rows:
            with self.subTest(case):
                # Act
                line = render_trace(trace)

                # Assert
                self.assertEqual(line, expected)
