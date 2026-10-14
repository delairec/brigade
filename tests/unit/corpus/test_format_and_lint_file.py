import unittest
from pathlib import Path

from brigade.corpus.format_and_lint_file import format_and_lint_file
from brigade.corpus.lint_corpus import LintReport
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest

FILE = Path("/state/brigade/runs/r1/progress.awawa")


class AwawaDouble:
    def __init__(self, lint_exit_code: int, lint_output: str):
        self.requests = []
        self.lint_exit_code = lint_exit_code
        self.lint_output = lint_output

    def run_process(self, request: ProcessRequest) -> ProcessRecord:
        self.requests.append(request)
        exit_code, stdout = (self.lint_exit_code, self.lint_output) if "lint" in request.argv else (0, "")
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr="", duration_ms=5
        )


class FormatAndLintFileTest(unittest.TestCase):
    def test_should_format_then_lint_the_file_naming_it_and_never_its_directory(self):
        # Arrange
        awawa = AwawaDouble(lint_exit_code=0, lint_output="")

        # Act
        format_and_lint_file(awawa.run_process, FILE)

        # Assert
        self.assertEqual(
            awawa.requests,
            [
                ProcessRequest(
                    argv=("awawa", "fmt", "/state/brigade/runs/r1/progress.awawa"),
                    cwd="/state/brigade/runs/r1",
                    timeout_s=30.0,
                    acceptable_exit_codes=EVERY_EXIT_CODE,
                ),
                ProcessRequest(
                    argv=("awawa", "lint", "--strict", "/state/brigade/runs/r1/progress.awawa"),
                    cwd="/state/brigade/runs/r1",
                    timeout_s=30.0,
                    acceptable_exit_codes=(0, 1),
                ),
            ],
        )

    def test_should_report_the_findings_of_the_lint(self):
        # Arrange
        awawa = AwawaDouble(lint_exit_code=1, lint_output="L014  error  progress.awawa:30:1\n")

        # Act
        report = format_and_lint_file(awawa.run_process, FILE)

        # Assert
        self.assertEqual(report, LintReport(clean=False, output="L014  error  progress.awawa:30:1"))

    def test_should_report_a_clean_file(self):
        # Arrange
        awawa = AwawaDouble(lint_exit_code=0, lint_output="")

        # Act
        report = format_and_lint_file(awawa.run_process, FILE)

        # Assert
        self.assertEqual(report, LintReport(clean=True, output=""))
