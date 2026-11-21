import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.page import COMMAND
from brigade.system.run_process import ProcessRecord
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

UNDOCUMENTED_EXIT_CODE = 3


def _answer_that_brigade_is_down(request) -> ProcessRecord:
    return ProcessRecord(
        argv=request.argv,
        cwd=request.cwd,
        exit_code=UNDOCUMENTED_EXIT_CODE,
        stdout="",
        stderr="brigade is down",
        duration_ms=0,
    )


class PageTextTest(unittest.TestCase):
    def test_should_print_the_page_alone(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "page": "home", "html": "<html></html>"})

        # Assert
        self.assertEqual(text, "<html></html>")


class PageTest(unittest.TestCase):
    def test_should_print_the_page_without_its_script_its_view_filled_from_the_dashboard(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = create_test_runtime(create_test_paths(root), run_process=_answer_that_brigade_is_down)

        # Act
        document = COMMAND.run(Namespace(page="home"), runtime)

        # Assert
        self.assertNotIn('<script src="/dashboard.js" defer></script>', document["html"])
        self.assertNotIn('<main id="view"></main>', document["html"])
