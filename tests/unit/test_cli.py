import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade import VERSION
from brigade.cli import main
from brigade.commands.tick import LOCK_NAME
from brigade.system.hold_lock import hold_lock

ADAPTER_MATRIX = (
    "| Supported client | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour"
    " | Graceful stop |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    "| claude-code | full | full | full | full | full | full | full | full | full |\n"
    "\n"
    "| Test-suite adapter | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour"
    " | Graceful stop |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    "| fake | full | full | fallback | fallback | fallback | fallback | fallback | fallback | fallback |\n"
    "\n"
    "Fallbacks:\n"
    "\n"
    "- no resume: a fresh launch from the progress file\n"
    "- no transcripts: brigade's journal of the run\n"
    "- no actions: one raw record per line of the client's output\n"
    "- no step count: steps null and the run held on the clock alone\n"
    "- no tool grants: the client's unattended mode and a disposable worktree for a reading slot\n"
    "- no reset hour: now plus thirty minutes\n"
    "- no graceful stop: the hard cut at the wall-time limit\n"
)


class MainTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.environment = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.root),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_STATE_HOME": str(self.root / "state"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
        }

    def run_main(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(arguments, self.environment)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def refuse(self, arguments: list[str]) -> int:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
            main(arguments, self.environment)
        return exit_.exception.code

    def ask_help(self, arguments: list[str]) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as exit_:
            main(arguments, self.environment)
        return exit_.exception.code, stdout.getvalue()


class MainHelpTest(MainTestCase):
    def test_should_list_every_command_when_the_line_names_none(self):
        # Act
        exit_code, page = self.ask_help(["--help"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertRegex(page, r"\n    ledger +read the event journal")


class MainVersionTest(MainTestCase):
    def test_should_print_the_version_as_a_json_document_when_asked(self):
        # Act
        exit_code, stdout, _ = self.run_main(["--version", "--json"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout), {"schema_version": 1, "version": VERSION})


class MainOfACommandTest(MainTestCase):
    def test_should_print_the_document_of_the_command_as_json_when_asked(self):
        # Act
        exit_code, stdout, _ = self.run_main(["processes", "list", "--json"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout)["schema_version"], 1)

    def test_should_print_the_text_of_the_command(self):
        # Act
        outcome = self.run_main(["processes", "list"])

        # Assert
        self.assertEqual(outcome, (0, "kind  id  instant  processes  failed\n", ""))

    def test_should_report_a_refusal_of_the_command_on_its_exit_code(self):
        # Act
        exit_code, _, stderr = self.run_main(["runs", "show", "20261019T090000Z-c0ffee"])

        # Assert
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr, "brigade runs show: no run 20261019T090000Z-c0ffee\n")


class MainOfACommandWithDiagnosticsTest(MainTestCase):
    def test_should_write_each_diagnostic_on_stderr(self):
        # Arrange
        ledger = self.root / "state" / "brigade" / "ledger"
        ledger.mkdir(parents=True)
        (ledger / "2026-10.jsonl").write_text("not json\n")

        # Act
        exit_code, _, stderr = self.run_main(["ledger"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, f"brigade ledger: skipped {ledger / '2026-10.jsonl'}:1: not JSON\n")


class MainOfAMisusedCommandTest(MainTestCase):
    def test_should_answer_the_usage_exit_code(self):
        # Act
        exit_code, _, stderr = self.run_main(["ledger", "--since", "2026-10-01"])

        # Assert
        self.assertEqual(exit_code, 2)
        self.assertEqual(stderr, "brigade ledger: --since needs --project\n")


class MainOfACommandFailingUnexpectedlyTest(MainTestCase):
    def test_should_print_the_traceback_and_answer_the_software_exit_code(self):
        # Arrange
        ticks = self.root / "state" / "brigade" / "ticks"
        ticks.mkdir(parents=True)
        (ticks / "20261019T090000Z.jsonl").write_bytes(b"\xff\n")

        # Act
        exit_code, _, stderr = self.run_main(["processes", "show", "20261019T090000Z"])

        # Assert
        self.assertEqual(exit_code, 70)
        self.assertEqual(stderr.splitlines()[-1].split(":")[0], "UnicodeDecodeError")


class MainOfACommandStandingDownTest(MainTestCase):
    def test_should_report_why_and_answer_success(self):
        # Arrange
        lock = self.root / "state" / "brigade" / "locks" / LOCK_NAME

        # Act
        with hold_lock(lock):
            exit_code, _, stderr = self.run_main(["tick", "--once"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, f"brigade tick: another tick holds {lock}\n")


class MainOfACommandRenderedAsMarkdownTest(MainTestCase):
    def test_should_print_the_markdown_of_the_command_when_asked(self):
        # Arrange
        empty_search_path = self.root / "bin"
        empty_search_path.mkdir()
        self.environment["PATH"] = str(empty_search_path)

        # Act
        exit_code, stdout, _ = self.run_main(["adapter", "matrix", "--markdown"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, ADAPTER_MATRIX)


class MainRefusalTest(MainTestCase):
    def test_should_refuse_a_command_line_naming_no_command_or_an_unknown_argument(self):
        for arguments in [[], ["--version", "--frobnicate"]]:
            with self.subTest(arguments=arguments):
                # Act
                exit_code = self.refuse(arguments)

                # Assert
                self.assertEqual(exit_code, 2)
