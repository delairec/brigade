import functools
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.run import COMMAND, run
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.resolve_plugin import PluginSources, resolve_plugin
from brigade.system.trail_writer import TrailWriter

NO_PATH_NEEDED = ""
UNKNOWN_CLIENT = "no-such-client"
UNKNOWN_PROCEDURE = "no-such-procedure"


def _report_nothing(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"the run of a command ran {request.argv}")


def _create_runtime(root: Path) -> Runtime:
    sources = PluginSources(executable_search_path=NO_PATH_NEEDED, run_process=_refuse_process)
    return Runtime(
        run_process=_refuse_process,
        spawn_process=_refuse_process,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path=NO_PATH_NEEDED,
        ),
        now=datetime(2026, 10, 8, 9, 0, 0, tzinfo=UTC),
        read_clock=lambda: datetime(2026, 10, 8, 9, 0, 0, tzinfo=UTC),
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=functools.partial(resolve_plugin, sources=sources),
    )


class RunClientPrecedenceTest(unittest.TestCase):
    def test_should_report_an_unknown_client_before_an_unknown_procedure(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text(f'client = "{UNKNOWN_CLIENT}"\n', encoding="utf-8")
        request = SimpleNamespace(
            procedure=UNKNOWN_PROCEDURE,
            slot="build",
            project=None,
            cwd=None,
            brief=None,
            arguments=(),
            run_id=None,
            detach=False,
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            run(request, _create_runtime(root))

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"no client adapter {UNKNOWN_CLIENT}: no built-in module and no brigade-client-{UNKNOWN_CLIENT} on PATH",
        )


class RunTextTest(unittest.TestCase):
    def test_should_count_the_segments_of_a_run_handed_over(self):
        # Arrange
        document = {
            "run": "20261007T090000Z-b70a01",
            "procedure": "deliver",
            "role": "builder",
            "slot": "build",
            "outcome": "done",
            "segments": 2,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "run 20261007T090000Z-b70a01: deliver as builder (build) done after 2 segments")


class RunExtraArgumentTest(unittest.TestCase):
    def test_should_leave_every_word_but_an_option_to_the_procedure(self):
        # Arrange
        rows = [
            ("an argument of the procedure", "task=B06", True),
            ("an unknown option", "--frobnicate", False),
            ("a word with no separator", "B06", True),
        ]
        for case, extra, expected_acceptance in rows:
            with self.subTest(case=case):
                # Act
                accepted = COMMAND.accept_extra_argument(extra)

                # Assert
                self.assertIs(accepted, expected_acceptance)
