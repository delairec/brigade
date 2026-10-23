import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.request_cancel import COMMAND
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class RequestCancelTest(unittest.TestCase):
    def test_should_answer_the_request_and_its_cancelled_status(self):
        # Arrange
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        processes = ScriptedProcesses()
        write_operational_corpus(directory)
        runtime = create_test_runtime(create_test_paths(directory), run_process=processes)
        config_root = runtime.paths.config_root
        (config_root / "requests.awawa").write_text("REQUEST shop_r2\n\tSTATUS planning\n", encoding="utf-8")
        processes.answer_entity(config_root, "REQUEST", "shop_r2", (("STATUS", "planning"),))
        message = "brigade request cancel: @REQUEST.shop_r2 cancelled"
        processes.answer_corpus_change(config_root, ("requests.awawa",), message)

        # Act
        document = COMMAND.run(Namespace(request="shop_r2"), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "request": "shop_r2", "status": "cancelled"})


class RequestCancelTextTest(unittest.TestCase):
    def test_should_name_the_request_and_its_status(self):
        # Arrange
        document = {"schema_version": 1, "request": "shop_r1", "status": "cancelled"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "@REQUEST.shop_r1 cancelled")


class RequestCancelExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class RequestCancelRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(request="shop_r1")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)
