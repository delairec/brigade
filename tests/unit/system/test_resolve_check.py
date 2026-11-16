import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.errors import BrigadeError
from brigade.system.check_places import CheckPlaces
from brigade.system.resolve_check import BuiltInCheck, ExecutableCheck, resolve_check
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

NO_EXECUTABLE_DIRECTORY = ""
SUBJECT = {"schema_version": 1, "project": "/srv/shop", "parameters": {"pr": "42"}, "collected": {}}
FAILED_COVERAGE = {"schema_version": 1, "name": "coverage", "verdict": "fail", "findings": ["cart.py: 80%"]}
COVERAGE_COMMAND = "/opt/checks/brigade-check-coverage"


class ResolveCheckRefusalTest(unittest.TestCase):
    def test_should_refuse_a_name_no_place_holds_naming_the_places(self):
        # Arrange
        places = CheckPlaces(
            project_directory=Path("/nonexistent/shop/.brigade/checks"),
            machine_directory=Path("/nonexistent/config/checks"),
            executable_search_path=NO_EXECUTABLE_DIRECTORY,
        )
        rows = [("coverage", "coverage"), ("../ancestry", "../ancestry")]
        for name, named in rows:
            with self.subTest(name=name):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    resolve_check(name, places)

                # Assert
                self.assertEqual(
                    str(refusal.exception),
                    f"no check {named} in /nonexistent/shop/.brigade/checks, in /nonexistent/config/checks,"
                    f" as brigade-check-{named} on PATH or among the built-ins of brigade/checks",
                )


class ExecutableCheckTest(unittest.TestCase):
    def test_should_answer_the_document_of_the_executable(self):
        # Arrange
        runner = RecordingProcessRunner({(COVERAGE_COMMAND,): ProcessAnswer(stdout=json.dumps(FAILED_COVERAGE))})
        check = ExecutableCheck(name="coverage", source="PATH", command=COVERAGE_COMMAND)

        # Act
        document = check.judge(SUBJECT, create_test_runtime(run_process=runner))

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "name": "coverage", "verdict": "fail", "findings": ["cart.py: 80%"]}
        )

    def test_should_run_the_executable_in_the_project_the_subject_on_its_standard_input(self):
        # Arrange
        runner = RecordingProcessRunner({(COVERAGE_COMMAND,): ProcessAnswer(stdout=json.dumps(FAILED_COVERAGE))})
        check = ExecutableCheck(name="coverage", source="PATH", command=COVERAGE_COMMAND)

        # Act
        check.judge(SUBJECT, create_test_runtime(run_process=runner))

        # Assert
        self.assertEqual(
            (runner.requests[0].cwd, json.loads(runner.requests[0].stdin)),
            ("/srv/shop", {"schema_version": 1, "project": "/srv/shop", "parameters": {"pr": "42"}, "collected": {}}),
        )

    def test_should_refuse_an_answer_that_is_not_a_check_document_naming_the_check(self):
        # Arrange
        rows = [
            ("Usage: coverage\n", "check coverage answered no JSON document"),
            (
                '{"schema_version": 1, "name": "coverage", "verdict": "maybe", "findings": []}',
                "check coverage answered no check document: verdict is 'maybe', not one of pass, fail",
            ),
        ]
        for stdout, expected_refusal in rows:
            with self.subTest(stdout=stdout):
                runner = RecordingProcessRunner({(COVERAGE_COMMAND,): ProcessAnswer(stdout=stdout)})
                check = ExecutableCheck(name="coverage", source="PATH", command=COVERAGE_COMMAND)

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    check.judge(SUBJECT, create_test_runtime(run_process=runner))

                # Assert
                self.assertEqual(str(refusal.exception), expected_refusal)


def answer_without_findings(subject: dict, runtime) -> dict:
    return {"schema_version": 1, "name": "ancestry", "verdict": "pass"}


class BuiltInCheckTest(unittest.TestCase):
    def test_should_refuse_an_answer_of_a_built_in_that_is_not_a_check_document(self):
        # Arrange
        module = SimpleNamespace(check=answer_without_findings)
        check = BuiltInCheck(name="ancestry", source="built-in", command="brigade.checks.ancestry", module=module)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check.judge(SUBJECT, create_test_runtime())

        # Assert
        self.assertEqual(str(refusal.exception), "check ancestry answered no check document: lacks the key findings")


class ResolveCheckOfAnExecutableTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.executable = Path(self.root.name) / "brigade-check-coverage"
        self.executable.write_text("#!/bin/sh\n")
        self.executable.chmod(0o755)

    def test_should_resolve_the_executable_on_path_by_its_command(self):
        # Arrange
        places = CheckPlaces(
            project_directory=Path("/nonexistent/shop/.brigade/checks"),
            machine_directory=Path("/nonexistent/config/checks"),
            executable_search_path=self.root.name,
        )

        # Act
        check = resolve_check("coverage", places)

        # Assert
        self.assertEqual(check, ExecutableCheck(name="coverage", source="PATH", command=str(self.executable)))
