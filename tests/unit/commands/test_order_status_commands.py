import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands import order_cancel, order_pause, order_resume
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

ACTIVE_ORDER = (("RECIPE", "nightly"), ("STATUS", "active"))


class OrderStatusTextTest(unittest.TestCase):
    def test_should_say_whether_the_status_of_the_order_changed(self):
        # Arrange
        rows = [
            ("an order paused", order_pause.COMMAND, "paused", True, "paused @ORDER.nightly"),
            ("an order already paused", order_pause.COMMAND, "paused", False, "@ORDER.nightly is already paused"),
            ("an order cancelled", order_cancel.COMMAND, "archived", True, "cancelled @ORDER.nightly"),
            (
                "an order already cancelled",
                order_cancel.COMMAND,
                "archived",
                False,
                "@ORDER.nightly is already archived",
            ),
            ("an order resumed", order_resume.COMMAND, "active", True, "resumed @ORDER.nightly"),
            ("an order already active", order_resume.COMMAND, "active", False, "@ORDER.nightly is already active"),
        ]
        for case, command, status, changed, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = command.render_text(
                    {"schema_version": 1, "order": "nightly", "status": status, "changed": changed}
                )

                # Assert
                self.assertEqual(text, expected_text)


class OrderStatusTest(unittest.TestCase):
    def test_should_set_the_order_in_the_status_its_command_names(self):
        # Arrange
        rows = [
            ("pause", order_pause.COMMAND, "brigade order pause: nightly", "paused", True),
            ("cancel", order_cancel.COMMAND, "brigade order cancel: nightly", "archived", True),
            ("resume", order_resume.COMMAND, "brigade order resume: nightly", "active", False),
        ]
        for case, command, message, expected_status, expected_change in rows:
            with self.subTest(case=case):
                directory = tempfile.TemporaryDirectory()
                self.addCleanup(directory.cleanup)
                processes = ScriptedProcesses()
                write_operational_corpus(Path(directory.name))
                runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=processes)
                config_root = runtime.paths.config_root
                (config_root / "orders.awawa").write_text(
                    'ORDER nightly\n\tRECIPE "nightly"\n\tSTATUS active\n', encoding="utf-8"
                )
                processes.answer_entity(config_root, "ORDER", "nightly", ACTIVE_ORDER)
                processes.answer_corpus_change(config_root, ("orders.awawa",), message)

                # Act
                document = command.run(Namespace(name="nightly"), runtime)

                # Assert
                self.assertEqual(
                    document,
                    {"schema_version": 1, "order": "nightly", "status": expected_status, "changed": expected_change},
                )
