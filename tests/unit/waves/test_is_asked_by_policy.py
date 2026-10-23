import tempfile
import unittest
from pathlib import Path

from brigade.waves.is_asked_by_policy import is_asked_by_policy
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class IsAskedByPolicyTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.processes.answer_entities(
            self.root / "config",
            "POLICY",
            {
                "depot_policy": (("PROJECT", "@PROJECT.depot"), ("WAVE_START", "ask")),
                "shop_policy": (("PROJECT", "@PROJECT.shop"), ("WAVE_START", "auto")),
            },
        )

    def test_should_ask_for_the_project_its_policy_names(self):
        # Act
        asked = is_asked_by_policy(self.runtime, "depot", "WAVE_START")

        # Assert
        self.assertTrue(asked)

    def test_should_not_ask_for_a_project_another_projects_policy_asks_for(self):
        # Act
        asked = is_asked_by_policy(self.runtime, "shop", "WAVE_START")

        # Assert
        self.assertFalse(asked)


if __name__ == "__main__":
    unittest.main()
