import tempfile
import unittest
from pathlib import Path

from brigade.orders.record_order import NewOrder, record_order
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class RecordOrderTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)
        self.root = self.runtime.paths.config_root
        self.orders = self.root / "orders.awawa"

    def test_should_write_an_order_of_a_project_with_its_words_and_parameters_on_a_schedule(self):
        # Arrange
        self.processes.answer_corpus_change(
            self.root, ("orders.awawa",), "brigade order new: @ORDER.usage_report_20261019T090000Z"
        )
        order = NewOrder(
            name="usage_report_20261019T090000Z",
            recipe="usage-report",
            project="oak",
            text="the cost of the last review",
            params=("pull_request=12", "depth=2"),
            every="daily@07:00",
        )

        # Act
        record_order(self.runtime, order)

        # Assert
        self.assertEqual(
            self.orders.read_text(encoding="utf-8"),
            "ORDER usage_report_20261019T090000Z\n"
            '\tRECIPE "usage-report"\n'
            "\tPROJECT @PROJECT.oak\n"
            '\tTEXT "the cost of the last review"\n'
            '\tPARAM "pull_request=12"\n'
            '\tPARAM "depth=2"\n'
            '\tEVERY "daily@07:00"\n'
            "\tSTATUS active\n",
        )

    def test_should_append_a_machine_wide_order_on_demand_after_the_recorded_orders(self):
        # Arrange
        self.orders.write_text('ORDER nightly\n\tRECIPE "nightly"\n\tSTATUS active\n', encoding="utf-8")
        self.processes.answer_corpus_change(
            self.root, ("orders.awawa",), "brigade order new: @ORDER.cleanup_20261019T090000Z"
        )
        order = NewOrder(
            name="cleanup_20261019T090000Z", recipe="cleanup", project=None, text=None, params=(), every=None
        )

        # Act
        record_order(self.runtime, order)

        # Assert
        self.assertEqual(
            self.orders.read_text(encoding="utf-8"),
            "ORDER nightly\n"
            '\tRECIPE "nightly"\n'
            "\tSTATUS active\n"
            "\n"
            "ORDER cleanup_20261019T090000Z\n"
            '\tRECIPE "cleanup"\n'
            "\tSTATUS active\n",
        )
