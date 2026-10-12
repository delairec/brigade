import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import brigade
from brigade.commands.doctor import _check_checkout
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.system.trail_writer import TrailWriter

GIT_ANSWERS = {
    "for-each-ref": "*\tde446f3\torigin/main\n",
    "rev-parse": "8885daa\n",
    "rev-list": "1\t0\n",
}


def _report_nothing(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"the checkout check ran {request.argv}")


def _refuse_resolution(kind: str, name: str):
    raise AssertionError(f"the checkout check resolved the {kind} plugin {name}")


def _answer_the_git_of_a_checkout_behind_its_upstream(request: ProcessRequest) -> ProcessRecord:
    return ProcessRecord(
        argv=request.argv,
        cwd=request.cwd,
        exit_code=0,
        stdout=GIT_ANSWERS[request.argv[1]],
        stderr="",
        duration_ms=0,
    )


def _create_runtime(root: Path) -> Runtime:
    return Runtime(
        run_process=_answer_the_git_of_a_checkout_behind_its_upstream,
        spawn_process=_refuse_process,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path="",
        ),
        now=datetime(2026, 10, 11, 9, 0, tzinfo=UTC),
        read_clock=lambda: datetime(2026, 10, 11, 9, 0, tzinfo=UTC),
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=_refuse_resolution,
    )


class DoctorCheckOfACheckoutTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.checkout = root / "checkout"
        (self.checkout / "brigade").mkdir(parents=True)
        self.runtime = _create_runtime(root)

    def test_should_warn_that_the_checkout_is_behind_its_upstream(self):
        # Arrange
        package_file = self.checkout / "brigade" / "__init__.py"

        # Act
        with mock.patch.object(brigade, "__file__", str(package_file)):
            items = _check_checkout(self.runtime)

        # Assert
        self.assertEqual(
            items,
            [
                {
                    "name": "checkout",
                    "kind": "optional",
                    "state": "warning",
                    "detail": f"{self.checkout} at de446f3, 1 behind origin/main at 8885daa",
                    "fallback": "git pull in the checkout",
                }
            ],
        )

    def test_should_report_no_checkout_when_brigade_runs_from_an_archive(self):
        # Arrange
        archive = Path(self.root.name).resolve() / "dist" / "brigade.pyz"
        archive.parent.mkdir()
        archive.write_text("")
        package_file = archive / "brigade" / "__init__.py"

        # Act
        with mock.patch.object(brigade, "__file__", str(package_file)):
            items = _check_checkout(self.runtime)

        # Assert
        self.assertEqual(items, [])
