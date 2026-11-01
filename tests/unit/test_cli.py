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

    def refuse(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as exit_,
        ):
            main(arguments, self.environment)
        return exit_.exception.code, stdout.getvalue(), stderr.getvalue()

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


class MainGroupHelpTest(MainTestCase):
    def assert_listed(self, page: str, action: str, expected_help: str) -> None:
        self.assertIn(f" {action} {expected_help} ", " ".join(page.split()) + " ")

    def test_should_list_each_action_with_the_help_its_record_declares(self):
        # Arrange
        rows = [
            ("adapter", "actions", "answer actions, the request read on stdin"),
            ("adapter", "launch-argv", "answer launch-argv, the request read on stdin"),
            ("adapter", "matrix", "print the capabilities every client adapter declares"),
            ("adapter", "parse-result", "answer parse-result, the request read on stdin"),
            ("adapter", "probe", "answer probe, the request read on stdin"),
            ("adapter", "resume-argv", "answer resume-argv, the request read on stdin"),
            ("adapter", "transcripts", "answer transcripts, the request read on stdin"),
            ("ledger", "budgets", "p50 and p90 steps per procedure over its last runs, and the step cap of each role"),
            ("ledger", "compare", "two ranges of days against each other, or one range against reference figures"),
            ("project", "add", "register a git repository in the operational corpus"),
            ("project", "list", "list every registered project"),
            ("project", "pause", "pause a project"),
            ("project", "resume", "resume a paused project"),
            ("project", "show", "print the fields of a project"),
            ("roles", "lint", "check the built-in and the machine role files"),
            ("roles", "list", "list the role, the source and the model of each slot"),
            ("roles", "show", "print the role file a slot resolves to"),
            ("runs", "list", "list every run with its state and outcome"),
            ("runs", "show", "print the summary of a run, its segments and its progress, and with --log its journal"),
            ("scheduler", "install", "install the scheduler config.toml names, or the default"),
            (
                "scheduler",
                "status",
                "report the scheduler installed, whether its tick is stale, the paused waves and the parked tasks",
            ),
        ]
        for group, action, expected_help in rows:
            with self.subTest(group=group, action=action):
                # Act
                exit_code, page = self.ask_help([group, "--help"])

                # Assert
                self.assertEqual(exit_code, 0)
                self.assert_listed(page, action, expected_help)


class MainVersionTest(MainTestCase):
    def test_should_print_the_version_as_a_line_of_text(self):
        # Act
        exit_code, stdout, _ = self.run_main(["--version"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, f"brigade {VERSION}\n")

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
        exit_code, _, stderr = self.run_main(["ledger", "compare", "--range", "2026-10-01..2026-10-02"])

        # Assert
        self.assertEqual(exit_code, 2)
        self.assertEqual(stderr, "brigade ledger compare: compare takes two --range, or one --range and --reference\n")


class MainOfACommandFailingUnexpectedlyTest(MainTestCase):
    def test_should_print_the_traceback_and_answer_the_software_exit_code(self):
        # Arrange
        tick_too_recent_to_expire = "29991231T000000Z"
        ticks = self.root / "state" / "brigade" / "ticks"
        ticks.mkdir(parents=True)
        (ticks / f"{tick_too_recent_to_expire}.jsonl").write_bytes(b"\xff\n")

        # Act
        exit_code, _, stderr = self.run_main(["processes", "show", tick_too_recent_to_expire])

        # Assert
        self.assertEqual(exit_code, 70)
        self.assertRegex(stderr, r"\ATraceback \(most recent call last\):\n(.*\n)*UnicodeDecodeError: [^\n]*\n\Z")


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
    def test_should_refuse_a_misused_command_line_with_the_usage_error_naming_what_is_wrong(self):
        # Arrange
        rows = [
            ([], r"^usage: brigade "),
            (["--frobnicate"], r"unrecognized arguments: --frobnicate\n$"),
            (["--version", "--frobnicate"], r"unrecognized arguments: --frobnicate\n$"),
            (["--json"], r"\nbrigade: error: no option given\n$"),
            (
                ["runs"],
                (
                    r"^usage: brigade runs \[-h\] \[--json\] \[--verbose\] action \.\.\.\n"
                    r"brigade runs: error: the following arguments are required: action\n$"
                ),
            ),
            (
                ["runs", "frobnicate"],
                r"invalid choice: 'frobnicate' \(choose from '?list'?, '?prune'?, '?show'?, '?stop'?\)\n$",
            ),
            (["frobnicate"], r"invalid choice: 'frobnicate' \(choose from '?adapter'?, .+, '?wave'?\)\n$"),
            (["runs", "show"], r"\nbrigade runs show: error: the following arguments are required: run\n$"),
            (
                ["ledger", "--wave", "tidepool_w16", "--project", "tidepool"],
                r"\nbrigade ledger: error: argument --project: not allowed with argument --wave\n$",
            ),
            (
                ["ledger", "--project", "tidepool", "--since", "yesterday"],
                r"\nbrigade ledger: error: argument --since: 'yesterday' is neither <n>d nor a day YYYY-MM-DD\n$",
            ),
            (
                ["ledger", "budgets", "--last", "0"],
                r"\nbrigade ledger budgets: error: argument --last: '0' is not a count of 1 or more\n$",
            ),
            (
                ["ledger", "compare"],
                r"\nbrigade ledger compare: error: the following arguments are required: --range\n$",
            ),
            (
                ["ledger", "compare", "--range", "2026-13-01..2026-13-02"],
                (
                    r"\nbrigade ledger compare: error: argument --range: '2026-13-01\.\.2026-13-02' is not a range"
                    r" START\.\.END of days YYYY-MM-DD\n$"
                ),
            ),
            (
                ["ledger", "compare", "--range", "2026-10-01..2026-10-02", "--reference", "steps=1"],
                (
                    r"\nbrigade ledger compare: error: argument --reference: 'steps' is not a reference measure:"
                    r" steps_to_first_edit_p50, task_run_steps_p50, oversized_output_steps_per_launch\n$"
                ),
            ),
        ]
        for arguments, expected_error in rows:
            with self.subTest(arguments=arguments):
                # Act
                exit_code, stdout, stderr = self.refuse(arguments)

                # Assert
                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout, "")
                self.assertRegex(stderr, expected_error)


class MainTrailTest(MainTestCase):
    def setUp(self):
        super().setUp()
        empty_search_path = self.root / "empty"
        empty_search_path.mkdir()
        self.environment["PATH"] = str(empty_search_path)
        self.ticks = self.root / "state" / "brigade" / "ticks"
        self.commands = self.root / "state" / "brigade" / "commands"

    def write_trails(self, *paths: Path) -> None:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")

    def test_should_write_the_trail_of_the_command_in_a_file_named_after_it(self):
        # Act
        self.run_main(["scheduler", "status", "--json"])

        # Assert
        [trail] = self.commands.iterdir()
        self.assertRegex(trail.name, r"^\d{8}T\d{6}Z-scheduler-status\.jsonl$")

    def test_should_render_each_record_on_stderr_under_a_verbose_given_before_the_command(self):
        # Act
        exit_code, _, stderr = self.run_main(["--verbose", "scheduler", "status"])

        # Assert
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "brigade scheduler status: ran crontab -l, not on PATH\n")

    def test_should_remove_the_expired_trails_before_the_command_runs(self):
        # Arrange
        expired_tick = self.ticks / "20000101T000000Z.jsonl"
        expired_command = self.commands / "20000101T000000Z-doctor.jsonl"
        future_command = self.commands / "29991231T000000Z-doctor.jsonl"
        self.write_trails(expired_tick, expired_command, future_command)

        # Act
        self.run_main(["scheduler", "status", "--json"])

        # Assert
        self.assertEqual(expired_tick.exists(), False)
        self.assertEqual(expired_command.exists(), False)
        self.assertEqual(future_command.exists(), True)
