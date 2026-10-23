import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.runtime import Invocation, build_runtime
from brigade.system.process_trace import ProcessTrace

TRACE = ProcessTrace(argv=("git", "status"), cwd="/srv/shop", outcome="exited", exit_code=0, duration_ms=12)


class BuildRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.environment = {
            "HOME": str(self.root),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_STATE_HOME": str(self.root / "state"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
        }

    def report(self, *, verbose: bool) -> str:
        runtime = build_runtime(Invocation(command="runs list", verbose=verbose), self.environment)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            runtime.trail.append(TRACE)
        return stderr.getvalue()

    def test_should_root_the_runtime_in_the_directories_of_the_environment(self):
        # Act
        runtime = build_runtime(Invocation(command="runs list", verbose=False), self.environment)

        # Assert
        self.assertEqual(runtime.paths.config_root, self.root / "config" / "brigade")
        self.assertEqual(runtime.paths.state_root, self.root / "state" / "brigade")
        self.assertEqual(runtime.entry_point.is_absolute(), True)

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
