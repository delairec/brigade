import tempfile
import unittest
from pathlib import Path

from brigade.waves.read_wave_start import read_wave_start
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadWaveStartTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)

    def answer_policy(self, fields: tuple[tuple[str, str], ...]) -> None:
        self.processes.answer_entities(self.root / "config", "POLICY", {"shop_policy": fields})

    def test_should_ask_under_a_policy_asking_for_the_wave_start(self):
        # Arrange
        self.answer_policy((("PROJECT", "@PROJECT.shop"), ("WAVE_START", "ask")))

        # Act
        wave_start = read_wave_start(self.runtime, "shop")

        # Assert
        self.assertEqual(wave_start, "ask")

    def test_should_start_on_its_own_under_a_policy_asking_for_the_plan_review_alone(self):
        # Arrange
        self.answer_policy((("PROJECT", "@PROJECT.shop"), ("PLAN_REVIEW", "ask"), ("WAVE_START", "auto")))

        # Act
        wave_start = read_wave_start(self.runtime, "shop")

        # Assert
        self.assertEqual(wave_start, "auto")


if __name__ == "__main__":
    unittest.main()
