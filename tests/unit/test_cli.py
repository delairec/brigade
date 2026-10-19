import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade import VERSION
from brigade.cli import main
from brigade.commands.tick import LOCK_NAME
from brigade.system.hold_lock import hold_lock


class MainTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        environment = mock.patch.dict(
            os.environ,
            {
                "HOME": str(self.root),
                "XDG_CONFIG_HOME": str(self.root / "config"),
                "XDG_STATE_HOME": str(self.root / "state"),
                "XDG_CACHE_HOME": str(self.root / "cache"),
            },
        )
        environment.start()
        self.addCleanup(environment.stop)

    def run_main(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(arguments)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def refuse(self, arguments: list[str]) -> int:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
            main(arguments)
        return exit_.exception.code


class MainVersionTest(MainTestCase):
    def test_should_print_the_version_as_a_json_document_when_asked(self):
        # Act
        exit_code, stdout, _ = self.run_main(["--version", "--json"])

        # Assert
        self.assertEqual((exit_code, json.loads(stdout)), (0, {"schema_version": 1, "version": VERSION}))


class MainOfACommandTest(MainTestCase):
    def test_should_print_the_document_of_the_command_as_json_when_asked(self):
        # Act
        exit_code, stdout, _ = self.run_main(["processes", "list", "--json"])

        # Assert
        self.assertEqual((exit_code, json.loads(stdout)["schema_version"]), (0, 1))

    def test_should_print_the_text_of_the_command_and_settle_its_trail(self):
        # Act
        exit_code, _, _ = self.run_main(["processes", "list"])

        # Assert
        self.assertEqual((exit_code, (self.root / "state" / "brigade" / "commands").is_dir()), (0, False))

    def test_should_report_a_refusal_of_the_command_on_its_exit_code(self):
        # Act
        exit_code, _, stderr = self.run_main(["runs", "show", "20261019T090000Z-c0ffee"])

        # Assert
        self.assertEqual((exit_code, stderr), (1, "brigade runs show: no run 20261019T090000Z-c0ffee\n"))


class MainOfACommandWithDiagnosticsTest(MainTestCase):
    def test_should_write_each_diagnostic_on_stderr(self):
        # Arrange
        ledger = self.root / "state" / "brigade" / "ledger"
        ledger.mkdir(parents=True)
        (ledger / "2026-10.jsonl").write_text("not json\n")

        # Act
        exit_code, _, stderr = self.run_main(["ledger"])

        # Assert
        self.assertEqual((exit_code, stderr), (0, f"brigade ledger: skipped {ledger / '2026-10.jsonl'}:1: not JSON\n"))


class MainOfAMisusedCommandTest(MainTestCase):
    def test_should_answer_the_usage_exit_code(self):
        # Act
        exit_code, _, stderr = self.run_main(["ledger", "--since", "2026-10-01"])

        # Assert
        self.assertEqual((exit_code, stderr), (2, "brigade ledger: --since needs --project\n"))


class MainOfACommandFailingUnexpectedlyTest(MainTestCase):
    def test_should_print_the_traceback_and_answer_the_software_exit_code(self):
        # Arrange
        ticks = self.root / "state" / "brigade" / "ticks"
        ticks.mkdir(parents=True)
        (ticks / "20261019T090000Z.jsonl").write_bytes(b"\xff\n")

        # Act
        exit_code, _, stderr = self.run_main(["processes", "show", "20261019T090000Z"])

        # Assert
        self.assertEqual((exit_code, stderr.splitlines()[-1].split(":")[0]), (70, "UnicodeDecodeError"))


class MainOfACommandStandingDownTest(MainTestCase):
    def test_should_report_why_and_answer_success(self):
        # Arrange
        lock = self.root / "state" / "brigade" / "locks" / LOCK_NAME

        # Act
        with hold_lock(lock):
            exit_code, _, stderr = self.run_main(["tick", "--once"])

        # Assert
        self.assertEqual((exit_code, stderr), (0, f"brigade tick: another tick holds {lock}\n"))


class MainOfACommandRenderedAsMarkdownTest(MainTestCase):
    def test_should_print_the_markdown_of_the_command_when_asked(self):
        # Arrange
        empty_search_path = self.root / "bin"
        empty_search_path.mkdir()

        # Act
        with mock.patch.dict(os.environ, {"PATH": str(empty_search_path)}):
            exit_code, stdout, _ = self.run_main(["adapter", "matrix", "--markdown"])

        # Assert
        self.assertEqual((exit_code, stdout.startswith(("|", "#"))), (0, True))


class MainRefusalTest(MainTestCase):
    def test_should_refuse_a_command_line_naming_no_command_or_an_unknown_argument(self):
        for arguments in [[], ["--version", "--frobnicate"]]:
            with self.subTest(arguments=arguments):
                # Act
                exit_code = self.refuse(arguments)

                # Assert
                self.assertEqual(exit_code, 2)
