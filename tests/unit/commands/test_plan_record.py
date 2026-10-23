import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.plan_record import COMMAND, plan_record
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

REQUEST = json.dumps(
    {
        "fields": [
            {"name": "PROJECT", "atoms": ["@PROJECT.app"]},
            {"name": "TEXT", "atoms": ['"Let the tides be planned"']},
            {"name": "STATUS", "atoms": ["planning"]},
        ]
    }
)
PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
APP = json.dumps(
    {
        "fields": [
            {"name": "PATH", "atoms": ['"/srv/app"']},
            {"name": "MAIN", "atoms": ['"main"']},
            {"name": "CORPUS", "atoms": ['"corpus"']},
            {"name": "FORGE", "atoms": ['"none"']},
        ]
    }
)
APP_WITHOUT_CORPUS = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})
PLAN = 'MILESTONE M4\n\tTITLE "Tides"\n\nTASK T9\n\tMILESTONE @MILESTONE.M4\n\tTITLE "Ebb"\n'
PLAN_LISTING = json.dumps({"entities": [{"type": "MILESTONE", "name": "M4"}, {"type": "TASK", "name": "T9"}]})
MILESTONE_M4 = json.dumps({"fields": [{"name": "TITLE", "atoms": ['"Tides"']}]})
TASK_T9 = json.dumps(
    {"fields": [{"name": "MILESTONE", "atoms": ["@MILESTONE.M4"]}, {"name": "TITLE", "atoms": ['"Ebb"']}]}
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

CORPUS_SITES = json.dumps({"entities": [{"type": "TASK", "name": "T1", "file": "corpus/tasks.awawa", "line": 1}]})
REQUEST_SITES = json.dumps({"entities": [{"type": "REQUEST", "name": "r1", "file": "requests.awawa", "line": 1}]})
FORGE = object()


def resolve_forge(kind: str, name: str, **places):
    return FORGE


REQUESTS = 'REQUEST r1\n\tPROJECT @PROJECT.app\n\tTEXT "Let the tides be planned"\n\tSTATUS planning\n'


class PlanRecordTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.plan_file = root / "plan.awawa"
        self.plan_file.write_text(PLAN)
        self.answers = {
            ("awawa", "show", "@REQUEST.r1"): ProcessAnswer(stdout=REQUEST),
            ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
            ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
            ("awawa", "show", str(self.plan_file)): ProcessAnswer(stdout=PLAN_LISTING),
            ("awawa", "show", "@MILESTONE.M4"): ProcessAnswer(stdout=MILESTONE_M4),
            ("awawa", "show", "@TASK.T9"): ProcessAnswer(stdout=TASK_T9),
            ("awawa", "new", "MILESTONE"): ProcessAnswer(stdout='MILESTONE M4\n\tTITLE ""\n'),
            ("awawa", "new", "TASK"): ProcessAnswer(stdout='TASK T9\n\tMILESTONE @MILESTONE.M\n\tTITLE ""\n'),
            ("awawa", "status", "--json"): ProcessAnswer(stdout=CORPUS_SITES),
            ("awawa", "fmt"): ProcessAnswer(),
            ("awawa", "lint"): ProcessAnswer(),
            ("git", "worktree"): ProcessAnswer(),
            ("git", "rev-parse", "--verify"): ProcessAnswer(exit_code=1),
            ("git", "switch"): ProcessAnswer(),
            ("git", "add"): ProcessAnswer(),
            ("git", "diff"): ProcessAnswer(exit_code=1),
            ("git", "commit"): ProcessAnswer(),
            ("git", "fetch"): ProcessAnswer(),
        }
        self.runtime = create_test_runtime(
            create_test_paths(root), run_process=ScriptedProcessRunner(self.answers).run, resolve_plugin=resolve_forge
        )
        config_root = self.runtime.paths.config_root
        self.answers["awawa", "status", "--json", str(config_root)] = ProcessAnswer(stdout=REQUEST_SITES)
        config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA REQUEST\n")
        self.runtime.paths.configuration_file.write_text("")
        (config_root / "requests.awawa").write_text(REQUESTS)

    def test_should_record_the_plan_on_its_plan_branch_merged_at_once_without_a_forge(self):
        # Arrange
        request = argparse.Namespace(request="r1", file=str(self.plan_file))

        # Act
        document = plan_record(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {"schema_version": 1, "request": "r1", "milestone": "M4", "branch": "plan/r1", "pr": None},
        )

    def test_should_refuse_a_project_that_declares_no_corpus(self):
        # Arrange
        self.answers["awawa", "show", "@PROJECT.app"] = ProcessAnswer(stdout=APP_WITHOUT_CORPUS)
        request = argparse.Namespace(request="r1", file=str(self.plan_file))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            plan_record(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.app declares no corpus")


class PlanRecordRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(request="r1", file="plan.awawa")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(request="r1", file="plan.awawa"))


class PlanRecordExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_plan_is_recorded(self):
        # Arrange
        document = {"request": "r1", "milestone": "M4", "branch": "plan/r1"}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class PlanRecordTextTest(unittest.TestCase):
    def test_should_name_the_request_the_milestone_and_the_branch(self):
        # Arrange
        document = {"request": "r1", "milestone": "M4", "branch": "plan/r1"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "recorded @REQUEST.r1 as @MILESTONE.M4 on plan/r1")
