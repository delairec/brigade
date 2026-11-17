import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.orders.change_order_status import change_order_status
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

ORDERS = 'ORDER nightly\n\tRECIPE "nightly"\n\tSTATUS active\n'
ACTIVE_ORDER = (("RECIPE", "nightly"), ("STATUS", "active"))
PAUSED_ORDER = (("RECIPE", "nightly"), ("STATUS", "paused"))
ARCHIVED_ORDER = (("RECIPE", "nightly"), ("STATUS", "archived"))


class ChangeOrderStatusTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)
        self.config_root = self.runtime.paths.config_root
        self.orders = self.config_root / "orders.awawa"
        self.orders.write_text(ORDERS, encoding="utf-8")

    def test_should_report_the_pause_of_an_active_order(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "ORDER", "nightly", ACTIVE_ORDER)
        self.processes.answer_corpus_change(self.config_root, ("orders.awawa",), "brigade order pause: nightly")

        # Act
        changed = change_order_status(self.runtime, "nightly", "paused")

        # Assert
        self.assertEqual(changed, {"schema_version": 1, "order": "nightly", "status": "paused", "changed": True})

    def test_should_write_the_cancel_of_an_order_as_archived_in_the_orders_file(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "ORDER", "nightly", ACTIVE_ORDER)
        self.processes.answer_corpus_change(self.config_root, ("orders.awawa",), "brigade order cancel: nightly")

        # Act
        change_order_status(self.runtime, "nightly", "archived")

        # Assert
        self.assertEqual(
            self.orders.read_text(encoding="utf-8"), 'ORDER nightly\n\tRECIPE "nightly"\n\tSTATUS archived\n'
        )

    def test_should_write_the_resume_of_a_paused_order_as_active(self):
        # Arrange
        self.orders.write_text('ORDER nightly\n\tRECIPE "nightly"\n\tSTATUS paused\n', encoding="utf-8")
        self.processes.answer_entity(self.config_root, "ORDER", "nightly", PAUSED_ORDER)
        self.processes.answer_corpus_change(self.config_root, ("orders.awawa",), "brigade order resume: nightly")

        # Act
        change_order_status(self.runtime, "nightly", "active")

        # Assert
        self.assertEqual(self.orders.read_text(encoding="utf-8"), ORDERS)

    def test_should_change_nothing_for_an_order_already_in_the_status(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "ORDER", "nightly", ACTIVE_ORDER)

        # Act
        changed = change_order_status(self.runtime, "nightly", "active")

        # Assert
        self.assertEqual(changed, {"schema_version": 1, "order": "nightly", "status": "active", "changed": False})

    def test_should_refuse_to_change_an_archived_order(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "ORDER", "nightly", ARCHIVED_ORDER)
        self.processes.answer_corpus_change(self.config_root, ("orders.awawa",), "brigade order resume: nightly")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            change_order_status(self.runtime, "nightly", "active")

        # Assert
        self.assertEqual(str(refusal.exception), "@ORDER.nightly is archived; its status no longer changes")
