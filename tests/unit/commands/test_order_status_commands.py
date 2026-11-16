import os
import tempfile
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from brigade.commands import order_cancel, order_pause, order_resume
from brigade.ledger.append_event import append_event
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.convert_order import Order
from brigade.orders.start_order_run import start_order_run
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.spawned_process_double import SpawnedProcessDouble

ACTIVE_ORDER = (("RECIPE", "nightly"), ("STATUS", "active"))
PARKED_RUN = "20261018T090000Z-aaaaaa"
NIGHTLY = Order(
    name="nightly", recipe="nightly", project=None, text=None, params=(), every=None, output=None, status="active"
)
NIGHTLY_RECIPE = {"name": "nightly", "max_wall": 30, "steps": [{"kind": "command"}, {"kind": "judge"}]}


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
                    {"schema_version": 1, "order": "nightly", "status": status, "changed": changed, "run": None}
                )

                # Assert
                self.assertEqual(text, expected_text)


class OrderStatusTest(unittest.TestCase):
    def test_should_set_the_order_in_the_status_its_command_names(self):
        # Arrange
        rows = [
            ("pause", order_pause.COMMAND, "brigade order pause: nightly", "paused", True, {}),
            ("cancel", order_cancel.COMMAND, "brigade order cancel: nightly", "archived", True, {}),
            ("resume", order_resume.COMMAND, "brigade order resume: nightly", "active", False, {"run": None}),
        ]
        for case, command, message, expected_status, expected_change, expected_run in rows:
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
                    {
                        "schema_version": 1,
                        "order": "nightly",
                        "status": expected_status,
                        "changed": expected_change,
                        **expected_run,
                    },
                )


class OrderResumeOfAParkedOrderTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.spawned = []
        self.runtime = create_test_runtime(
            create_test_paths(Path(directory.name)), run_process=processes, spawn_process=self.spawn
        )
        self.config_root = self.runtime.paths.config_root
        (self.config_root / "orders.awawa").write_text(
            'ORDER nightly\n\tRECIPE "nightly"\n\tSTATUS active\n', encoding="utf-8"
        )
        processes.answer_entity(self.config_root, "ORDER", "nightly", ACTIVE_ORDER)
        processes.answer_corpus_change(self.config_root, ("orders.awawa",), "brigade order resume: nightly")
        self.order_record = self.runtime.paths.state_root / "runs" / PARKED_RUN / "order.json"

    def spawn(self, request):
        self.spawned.append((request.argv[2:], request.cwd))
        return SpawnedProcessDouble(pid=os.getpid())

    def _park(self) -> None:
        start_order_run(self.runtime, NIGHTLY, NIGHTLY_RECIPE, PARKED_RUN)
        os.utime(self.order_record, (0, 0))
        append_event(
            self.runtime.paths,
            FIXED_NOW,
            OrderParked(project=None, kind="nightly", order="nightly", run=PARKED_RUN, step="2-judge", reason="red"),
        )

    def test_should_relaunch_the_parked_run_of_the_order_at_its_first_undone_step(self):
        # Arrange
        self._park()

        # Act
        document = order_resume.COMMAND.run(Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(document["run"], PARKED_RUN)
        self.assertEqual(self.spawned, [(("order", "run", "nightly", "--run-id", PARKED_RUN), str(self.config_root))])

    def test_should_record_the_parked_run_started_again_so_that_the_order_is_no_longer_parked(self):
        # Arrange
        self._park()

        # Act
        order_resume.COMMAND.run(Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(
            read_ledger(self.runtime.paths.state_root).entries[-1].event,
            OrderStarted(project=None, kind="nightly", order="nightly", run=PARKED_RUN),
        )

    def test_should_count_the_max_wall_of_the_relaunched_run_from_its_resume(self):
        # Arrange
        self._park()

        # Act
        order_resume.COMMAND.run(Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(datetime.fromtimestamp(self.order_record.stat().st_mtime, UTC), FIXED_NOW)

    def test_should_launch_no_run_for_an_order_that_is_not_parked(self):
        # Act
        order_resume.COMMAND.run(Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(self.spawned, [])

    def test_should_say_which_parked_run_it_relaunched(self):
        # Arrange
        rows = [
            ("a paused order resumed", True, "resumed @ORDER.nightly; run 20261018T090000Z-aaaaaa relaunched"),
            (
                "an active order parked",
                False,
                "@ORDER.nightly is already active; run 20261018T090000Z-aaaaaa relaunched",
            ),
        ]
        for case, changed, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = order_resume.COMMAND.render_text(
                    {"schema_version": 1, "order": "nightly", "status": "active", "changed": changed, "run": PARKED_RUN}
                )

                # Assert
                self.assertEqual(text, expected_text)
