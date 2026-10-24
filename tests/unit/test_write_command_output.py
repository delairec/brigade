import argparse
import io
import unittest

from brigade.command import Command
from brigade.write_command_output import OutputStreams, write_command_output

RESULT = {"schema_version": 1, "runs": 2, "skipped": ["run r9 skipped"]}
NO_OPTION = argparse.Namespace()


def run_nothing(request, runtime) -> dict:
    return RESULT


def read_options(options):
    return options


def render_count(document: dict) -> str:
    return f"{document['runs']} runs"


def render_count_as_markdown(document: dict) -> str:
    return f"**{document['runs']}** runs"


def render_passed_warning(document: dict) -> str:
    return "1 warning\n"


def decide_three(document: dict) -> int:
    return 3


def describe_skipped(result: dict) -> list[str]:
    return result["skipped"]


def select_counts(result: dict) -> dict:
    return {"runs": result["runs"]}


def create_command(**changes) -> Command:
    return Command(
        **{
            "path": ("runs", "list"),
            "help": "list the runs",
            "run": run_nothing,
            "read_request": read_options,
            "render_text": render_count,
            "decide_exit_code": decide_three,
            **changes,
        }
    )


class WriteCommandOutputTestCase(unittest.TestCase):
    def write(self, command: Command, options: argparse.Namespace) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        exit_code = write_command_output(command, RESULT, options, OutputStreams(stdout=stdout, stderr=stderr))
        return exit_code, stdout.getvalue(), stderr.getvalue()


class WriteCommandOutputAsTextTest(WriteCommandOutputTestCase):
    def test_should_write_the_text_of_the_document_and_answer_its_exit_code(self):
        # Act
        written = self.write(create_command(), NO_OPTION)

        # Assert
        self.assertEqual(written, (3, "2 runs\n", ""))

    def test_should_write_the_diagnostics_of_the_result_on_stderr(self):
        # Act
        written = self.write(create_command(describe_diagnostics=describe_skipped), NO_OPTION)

        # Assert
        self.assertEqual(written, (3, "2 runs\n", "brigade runs list: run r9 skipped\n"))


class WriteCommandOutputAsAskedTest(WriteCommandOutputTestCase):
    def test_should_write_the_document_selected_from_the_result_as_json(self):
        # Act
        written = self.write(create_command(select_document=select_counts), argparse.Namespace(json=True))

        # Assert
        self.assertEqual(written, (3, '{"runs": 2}\n', ""))

    def test_should_write_the_markdown_of_the_document(self):
        # Act
        written = self.write(
            create_command(render_markdown=render_count_as_markdown), argparse.Namespace(json=False, markdown=True)
        )

        # Assert
        self.assertEqual(written, (3, "**2** runs\n", ""))


class WriteCommandOutputOfAPassthroughTest(WriteCommandOutputTestCase):
    def test_should_pass_the_output_and_the_error_output_through_as_they_are(self):
        # Act
        written = self.write(create_command(render_passed_stderr=render_passed_warning), argparse.Namespace(json=True))

        # Assert
        self.assertEqual(written, (3, "2 runs", "1 warning\n"))

    def test_should_write_the_diagnostics_before_the_passed_error_output(self):
        # Act
        written = self.write(
            create_command(describe_diagnostics=describe_skipped, render_passed_stderr=render_passed_warning),
            argparse.Namespace(json=True),
        )

        # Assert
        self.assertEqual(written, (3, "2 runs", "brigade runs list: run r9 skipped\n1 warning\n"))
