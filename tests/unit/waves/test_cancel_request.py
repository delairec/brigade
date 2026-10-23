import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.waves.cancel_request import cancel_request
from tests.unit.scripted_processes import ScriptedProcesses

REQUESTS = (
    "REQUEST shop_r1\n\tPROJECT @PROJECT.shop\n\tSTATUS planned\n\n\n"
    "REQUEST shop_r3\n\tPROJECT @PROJECT.shop\n\tSTATUS cancelled\n"
)
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class CancelRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)
        self.config_root = self.runtime.paths.config_root
        self.requests = self.config_root / "requests.awawa"
        self.requests.write_text(REQUESTS, encoding="utf-8")

    def test_should_write_the_cancelled_status_in_a_request_planning_or_planned(self):
        for status in ["planning", "planned"]:
            with self.subTest(status=status):
                # Arrange
                self.requests.write_text(REQUESTS, encoding="utf-8")
                self.processes.answer_entity(self.config_root, "REQUEST", "shop_r1", (("STATUS", status),))
                message = "brigade request cancel: @REQUEST.shop_r1 cancelled"
                self.processes.answer_corpus_change(self.config_root, ("requests.awawa",), message)

                # Act
                cancel_request(self.runtime, "shop_r1")

                # Assert
                self.assertEqual(
                    self.requests.read_text(encoding="utf-8"),
                    "REQUEST shop_r1\n\tPROJECT @PROJECT.shop\n\tSTATUS cancelled\n\n\n"
                    "REQUEST shop_r3\n\tPROJECT @PROJECT.shop\n\tSTATUS cancelled\n",
                )

    def test_should_refuse_a_request_no_longer_planning_or_planned(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "REQUEST", "shop_r3", (("STATUS", "cancelled"),))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            cancel_request(self.runtime, "shop_r3")

        # Assert
        self.assertEqual(str(raised.exception), "@REQUEST.shop_r3 is cancelled")
