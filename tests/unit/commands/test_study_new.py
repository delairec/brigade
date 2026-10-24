import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import ANY

from brigade.commands.study_new import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.plugin_double import PluginDouble

TIDEPOOL_PROJECT = (("PATH", "/home/user/tidepool"),)
MACHINE_WIDE = None
CORPUS_CHANGE_OUTPUTS = {
    ("awawa", "show", "ANSWER"): "",
    ("awawa", "fmt"): "",
    ("awawa", "lint"): "",
    ("git", "add"): "",
    ("git", "diff"): "",
}


class StudyNewTextTest(unittest.TestCase):
    def test_should_say_when_the_study_runs(self):
        # Arrange
        rows = [
            ("a scheduled study", {"every": "1d"}, "@STUDY.health recorded, every 1d"),
            (
                "a study run at once",
                {"every": None, "run": "20261019T090000Z-e10d04", "state": "done"},
                "@STUDY.health recorded, run 20261019T090000Z-e10d04 done",
            ),
        ]
        for case, schedule, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text({"schema_version": 1, "study": "health", **schedule})

                # Assert
                self.assertEqual(text, expected_text)


class StudyNewExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class StudyNewRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(name="health")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class StudyNewOfAScheduledStudyTest(unittest.TestCase):
    def test_should_record_a_scheduled_study_without_running_it(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        run_process = create_machine_double({"PROJECT": {"tidepool": TIDEPOOL_PROJECT}}, CORPUS_CHANGE_OUTPUTS)
        request = Namespace(
            name="health",
            title="the health of the tidepool",
            question=None,
            project="tidepool",
            collector=["runs-list"],
            slot="report",
            every="daily@06:00",
            output="file:/home/user/health.md",
            answer="ANSWER",
        )

        # Act
        document = COMMAND.run(request, create_test_runtime(create_test_paths(root), run_process=run_process))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "study": "health", "every": "daily@06:00"})

    def test_should_record_a_machine_wide_study_with_no_project(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        request = Namespace(
            name="health",
            title="the health of the machine",
            question=None,
            project=MACHINE_WIDE,
            collector=["runs-list"],
            slot="report",
            every="daily@06:00",
            output="file:/home/user/health.md",
            answer="ANSWER",
        )

        # Act
        document = COMMAND.run(
            request,
            create_test_runtime(create_test_paths(root), run_process=create_machine_double({}, CORPUS_CHANGE_OUTPUTS)),
        )

        # Assert
        self.assertEqual(document, {"schema_version": 1, "study": "health", "every": "daily@06:00"})
        self.assertEqual(
            (root / "config" / "studies.awawa").read_text(encoding="utf-8"),
            "STUDY health\n"
            '\tTITLE "the health of the machine"\n'
            '\tCOLLECTOR "runs-list"\n'
            "\tSLOT report\n"
            '\tEVERY "daily@06:00"\n'
            '\tOUTPUT "file:/home/user/health.md"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS active\n",
        )


HEALTH_STUDY = (
    ("TITLE", "the health of the machine"),
    ("COLLECTOR", "runs-list"),
    ("SLOT", "report"),
    ("OUTPUT", "file:/home/user/health.md"),
    ("ANSWER", "ANSWER"),
    ("STATUS", "active"),
)


def _resolve_no_collector(kind: str, name: str, **places):
    if kind == "collector":
        raise BrigadeError(f"no collector {name}")
    return PluginDouble(kind=kind, name=name)


class StudyNewOfAStudyOnDemandTest(unittest.TestCase):
    def test_should_run_a_study_with_no_schedule_at_once(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        run_process = create_machine_double({"STUDY": {"health": HEALTH_STUDY}}, CORPUS_CHANGE_OUTPUTS)
        on_demand = None
        request = Namespace(
            name="health",
            title="the health of the machine",
            question=None,
            project=MACHINE_WIDE,
            collector=["runs-list"],
            slot="report",
            every=on_demand,
            output="file:/home/user/health.md",
            answer="ANSWER",
        )

        # Act
        document = COMMAND.run(
            request,
            create_test_runtime(create_test_paths(root), run_process=run_process, resolve_plugin=_resolve_no_collector),
        )

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "study": "health", "every": None, "run": ANY, "state": "parked"}
        )


class StudyNewOfAStudyWhoseOutputIsTheInboxTest(unittest.TestCase):
    def test_should_record_no_study_it_refuses(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        request = Namespace(
            name="health",
            title="the health of the machine",
            question=None,
            project=MACHINE_WIDE,
            collector=["runs-list"],
            slot="report",
            every="daily@06:00",
            output="inbox",
            answer="ANSWER",
        )
        runtime = create_test_runtime(
            create_test_paths(root), run_process=create_machine_double({}, CORPUS_CHANGE_OUTPUTS)
        )

        # Act
        with self.assertRaises(BrigadeError):
            COMMAND.run(request, runtime)

        # Assert
        self.assertFalse((root / "config" / "studies.awawa").exists())
