import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.runtime import Invocation, build_runtime
from brigade.system.process_trace import ProcessTrace

TRACE = ProcessTrace(argv=("git", "status"), cwd="/srv/shop", outcome="exited", exit_code=0, duration_ms=12)


class BuildRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        environment = mock.patch.dict(
            os.environ,
            {
                "HOME": str(self.root),
                "XDG_CONFIG_HOME": str(self.root / "config"),
                "XDG_STATE_HOME": str(self.root / "state"),
                "XDG_CACHE_HOME": str(self.root / "cache"),
            },
        )
        environment.start()
        self.addCleanup(environment.stop)

    def report(self, *, verbose: bool) -> str:
        runtime = build_runtime(Invocation(command="runs list", verbose=verbose))
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            runtime.trail.append(TRACE)
        return stderr.getvalue()

    def test_should_root_the_runtime_in_the_directories_of_the_environment(self):
        # Act
        runtime = build_runtime(Invocation(command="runs list", verbose=False))

        # Assert
        self.assertEqual(
            (runtime.paths.config_root, runtime.paths.state_root, runtime.entry_point.is_absolute()),
            (self.root / "config" / "brigade", self.root / "state" / "brigade", True),
        )

    def test_should_report_each_process_on_stderr_when_verbose(self):
        # Act
        report = self.report(verbose=True)

        # Assert
        self.assertEqual(report, "brigade runs list: ran git status, exit 0 in 12 ms\n")

    def test_should_report_nothing_when_quiet(self):
        # Act
        report = self.report(verbose=False)

        # Assert
        self.assertEqual(report, "")
