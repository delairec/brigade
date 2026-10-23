import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.wave_resume import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

EVERY_PAUSE = None
WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-09-30T22:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "tasks": ["T7"],
}


def _pause(wave: str, reason: str) -> dict:
    return {
        "schema_version": 1,
        "ts": "2026-10-01T00:15:00Z",
        "event": "wave.paused",
        "wave": wave,
        "reason": reason,
        "resume_at": None,
    }


class WaveResumeTextTest(unittest.TestCase):
    def test_should_name_each_wave_resumed(self):
        # Arrange
        rows = [
            ("no wave", [], "no wave is paused on the forge account"),
            (
                "two waves",
                [{"wave": "tidepool_w16", "reason": "quota"}, {"wave": "tidepool_w17", "reason": "quota"}],
                "wave tidepool_w16 resumed\nwave tidepool_w17 resumed",
            ),
        ]
        for case, resumed, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text({"schema_version": 1, "resumed": resumed})

                # Assert
                self.assertEqual(text, expected_text)


class WaveResumeExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1, "resumed": []})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveResumeRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(wave=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveResumeOfThePausedWavesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_test_runtime(create_test_paths(self.root))

    def test_should_resume_every_wave_paused_on_the_forge_account_only(self):
        # Arrange
        write_ledger(
            self.root,
            [_pause("tidepool_w16", "forge_account"), _pause("tidepool_w17", "quota")],
        )

        # Act
        document = COMMAND.run(Namespace(wave=EVERY_PAUSE), self.runtime)

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "resumed": [{"wave": "tidepool_w16", "reason": "forge_account"}]}
        )

    def test_should_resume_the_wave_named_whatever_its_pause(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, _pause("tidepool_w16", "quota")])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16"), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "resumed": [{"wave": "tidepool_w16", "reason": "quota"}]})

    def test_should_refuse_to_resume_a_running_wave(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w16"), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the wave tidepool_w16 is running, not paused")

    def test_should_refuse_to_resume_a_wave_no_wave_started_names(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w17"), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no wave.started names the wave tidepool_w17")
