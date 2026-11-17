import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.wave_parked import WaveParked
from brigade.preflights.run_preflight import PreflightOutcome
from brigade.waves.start_preflighted_wave import PreflightedWaveStart, start_preflighted_wave
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

FAILED_PREFLIGHT = PreflightOutcome(
    result="fail",
    checks=[
        {
            "name": "forge_logins",
            "result": "fail",
            "findings": ["gh printed no token for the login prudence-bot, bound to review"],
        }
    ],
    collected={},
)
PASSED_PREFLIGHT = PreflightOutcome(
    result="ok", checks=[{"name": "forge_logins", "result": "ok", "findings": []}], collected={}
)
STARTED = {"wave": "shop_w3", "project": "shop", "tasks": ["S1"]}


class StartPreflightedWaveTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.paths = create_test_paths(Path(directory.name))
        self.steps = []

    def preflight(self, outcome: PreflightOutcome):
        def run() -> PreflightOutcome:
            self.steps.append("preflight")
            return outcome

        return run

    def start(self) -> dict:
        self.steps.append("start")
        return STARTED

    def start_wave(self, outcome: PreflightOutcome) -> str:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            start_preflighted_wave(
                create_test_runtime(self.paths),
                PreflightedWaveStart(preflight=self.preflight(outcome), start=self.start),
            )
        return stderr.getvalue()

    def test_should_pause_the_wave_on_the_forge_account_before_any_run_when_its_preflight_fails(self):
        # Act
        self.start_wave(FAILED_PREFLIGHT)

        # Assert
        self.assertEqual(
            read_ledger(self.paths.state_root).entries[-1].event,
            WaveParked(wave="shop_w3", reason="forge_account"),
        )

    def test_should_name_the_findings_of_the_failed_preflight_on_stderr(self):
        # Act
        stderr = self.start_wave(FAILED_PREFLIGHT)

        # Assert
        self.assertEqual(
            stderr,
            "brigade tick: the wave shop_w3 parked before any run: gh printed no token for the login prudence-bot,"
            " bound to review; repair the login, then run brigade wave resume shop_w3\n",
        )

    def test_should_leave_the_wave_running_when_its_preflight_passes(self):
        # Act
        self.start_wave(PASSED_PREFLIGHT)

        # Assert
        self.assertEqual(read_ledger(self.paths.state_root).entries, ())

    def test_should_run_the_preflight_before_it_starts_the_wave(self):
        # Act
        self.start_wave(PASSED_PREFLIGHT)

        # Assert
        self.assertEqual(self.steps, ["preflight", "start"])
