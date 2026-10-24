import functools
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.roles_list import COMMAND
from brigade.errors import BrigadeError
from brigade.system.resolve_plugin import PluginSources, resolve_plugin
from brigade.system.run_process import ProcessRecord, ProcessRequest
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.refuse_to_run import refuse_to_run

PROBE_ANSWER = {
    "schema_version": 1,
    "client": "double",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {"standard": "model-standard", "deep": "model-deep"},
}


OTHER_PROBE_ANSWER = {**PROBE_ANSWER, "client": "other", "models": {"deep": "other-deep"}}
PLANNER_FIELDS = [
    {"name": "WORK", "atoms": ['"the plan of a wave"']},
    {"name": "REASONING", "atoms": ["deep"]},
    {"name": "CAPABILITY", "atoms": ["read"]},
    {"name": "BUDGET", "atoms": ["40"]},
    {"name": "RETURNS", "atoms": ['"the plan"']},
]
PLANNER_PACKAGE = 'AGENT planner\n\tWORK "the plan of a wave"\n'
AWAWA_ANSWERS = {"show": json.dumps({"fields": PLANNER_FIELDS}), "context": PLANNER_PACKAGE}
NO_EXECUTABLE_DIRECTORY = ""


class ClientDouble:
    def answer(self, operation: str, request: dict) -> dict:
        return PROBE_ANSWER


class OtherClientDouble:
    def answer(self, operation: str, request: dict) -> dict:
        return OTHER_PROBE_ANSWER


class ReasoningTableClientDouble:
    def answer(self, operation: str, request: dict) -> dict:
        return {**PROBE_ANSWER, "models": {"light": request["reasoning_table"]["light"]["model"]}}


CLIENT_DOUBLES = {"double": ClientDouble(), "other": OtherClientDouble()}


def _resolve_the_client_double(kind: str, name: str, **places):
    return ClientDouble()


def _resolve_the_client_double_named(kind: str, name: str, **places):
    return CLIENT_DOUBLES[name]


def _resolve_the_reasoning_table_client_double(kind: str, name: str, **places):
    return ReasoningTableClientDouble()


def _answer_awawa(request: ProcessRequest) -> ProcessRecord:
    return ProcessRecord(
        argv=request.argv,
        cwd=request.cwd,
        exit_code=0,
        stdout=AWAWA_ANSWERS[request.argv[1]],
        stderr="",
        duration_ms=1,
    )


class RolesListTextTest(unittest.TestCase):
    def test_should_mark_a_slot_with_no_model_bound_by_a_dash(self):
        # Arrange
        document = {
            "schema_version": 1,
            "client": None,
            "slot_clients": {},
            "roles": [{"slot": "plan", "role": "planner", "source": "built-in", "model": None}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "slot  role     source    model\nplan  planner  built-in  -\nanswers for no client")

    def test_should_print_the_model_a_slot_is_bound_to(self):
        # Arrange
        document = {
            "schema_version": 1,
            "client": "double",
            "slot_clients": {},
            "roles": [{"slot": "build", "role": "builder", "source": "built-in", "model": "model-standard"}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "slot   role     source    model\nbuild  builder  built-in  model-standard\nanswers for double",
        )

    def test_should_print_under_the_table_the_client_it_answers_for_and_the_slot_bound_to_another_client(self):
        # Arrange
        document = {
            "schema_version": 1,
            "client": "double",
            "slot_clients": {"review": "other"},
            "roles": [{"slot": "review", "role": "reviewer", "source": "built-in", "model": "other-deep"}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text.splitlines()[-2:],
            ["answers for double", "slot review runs on other"],
        )


class RolesListExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Arrange
        document = {"schema_version": 1, "client": None, "slot_clients": {}, "roles": []}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class RolesListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(json=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RolesListOfTheMachineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_bind_no_model_when_no_client_is_configured(self):
        # Arrange
        runtime = create_test_runtime(create_test_paths(self.root))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["roles"][1], {"slot": "build", "role": "builder", "source": "built-in", "model": None}
        )

    def test_should_bind_the_model_the_client_names_for_the_reasoning_of_the_role(self):
        # Arrange
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text('client = "double"\n', encoding="utf-8")
        runtime = create_test_runtime(create_test_paths(self.root), resolve_plugin=_resolve_the_client_double)

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["roles"][1],
            {"slot": "build", "role": "builder", "source": "built-in", "model": "model-standard"},
        )

    def test_should_resolve_every_slot_to_its_built_in_role_with_no_model_bound(self):
        # Arrange
        runtime = create_test_runtime(create_test_paths(self.root))

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "client": None,
                "slot_clients": {},
                "roles": [
                    {"slot": "plan", "role": "planner", "source": "built-in", "model": None},
                    {"slot": "build", "role": "builder", "source": "built-in", "model": None},
                    {"slot": "review", "role": "reviewer", "source": "built-in", "model": None},
                    {"slot": "remediate", "role": "remediator", "source": "built-in", "model": None},
                    {"slot": "rebase", "role": "rebaser", "source": "built-in", "model": None},
                    {"slot": "report", "role": "reporter", "source": "built-in", "model": None},
                    {"slot": "triage", "role": "triager", "source": "built-in", "model": None},
                    {"slot": "rules", "role": "rulewriter", "source": "built-in", "model": None},
                    {"slot": "explore", "role": "explorer", "source": "built-in", "model": None},
                ],
            },
        )

    def test_should_hand_the_client_the_reasoning_table_of_the_configuration(self):
        # Arrange
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text(
            'client = "double"\n[reasoning.light]\nmodel = "model-light"\neffort = "low"\n', encoding="utf-8"
        )
        runtime = create_test_runtime(
            create_test_paths(self.root), resolve_plugin=_resolve_the_reasoning_table_client_double
        )

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["roles"][4], {"slot": "rebase", "role": "rebaser", "source": "built-in", "model": "model-light"}
        )


class RolesListOfAMachineBindingASlotToAnotherClientTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()

    def test_should_name_the_slot_bound_to_another_client_with_that_client_and_the_model_it_binds(self):
        # Arrange
        (self.root / "config" / "config.toml").write_text(
            'client = "double"\n[slot_clients]\nbuild = "double"\nreview = "other"\n', encoding="utf-8"
        )
        runtime = create_test_runtime(create_test_paths(self.root), resolve_plugin=_resolve_the_client_double_named)

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "client": "double",
                "slot_clients": {"review": "other"},
                "roles": [
                    {"slot": "plan", "role": "planner", "source": "built-in", "model": "model-deep"},
                    {"slot": "build", "role": "builder", "source": "built-in", "model": "model-standard"},
                    {"slot": "review", "role": "reviewer", "source": "built-in", "model": "other-deep"},
                    {"slot": "remediate", "role": "remediator", "source": "built-in", "model": "model-standard"},
                    {"slot": "rebase", "role": "rebaser", "source": "built-in", "model": None},
                    {"slot": "report", "role": "reporter", "source": "built-in", "model": "model-standard"},
                    {"slot": "triage", "role": "triager", "source": "built-in", "model": "model-standard"},
                    {"slot": "rules", "role": "rulewriter", "source": "built-in", "model": "model-deep"},
                    {"slot": "explore", "role": "explorer", "source": "built-in", "model": None},
                ],
            },
        )

    def test_should_refuse_a_slot_client_no_adapter_carries_naming_it(self):
        # Arrange
        (self.root / "config" / "config.toml").write_text('[slot_clients]\nreview = "frobnicate"\n', encoding="utf-8")
        sources = PluginSources(executable_search_path=NO_EXECUTABLE_DIRECTORY, run_process=refuse_to_run)
        runtime = create_test_runtime(
            create_test_paths(self.root), resolve_plugin=functools.partial(resolve_plugin, sources=sources)
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "no client adapter frobnicate: no built-in module and no brigade-client-frobnicate on PATH",
        )


class RolesListOfAMachineBindingASlotToAnAgentEntityTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()

    def test_should_leave_an_agent_entity_no_row_names_without_a_slot(self):
        # Arrange
        (self.root / "config" / "config.toml").write_text(
            f'instructions = "{self.root / "instructions"}"\n[slots]\nplan = "planner"\n', encoding="utf-8"
        )
        runtime = create_test_runtime(create_test_paths(self.root), run_process=_answer_awawa)

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["roles"],
            [
                {"slot": "plan", "role": "planner", "source": "instructions", "model": None},
                {"slot": "build", "role": "builder", "source": "built-in", "model": None},
                {"slot": "review", "role": "reviewer", "source": "built-in", "model": None},
                {"slot": "remediate", "role": "remediator", "source": "built-in", "model": None},
                {"slot": "rebase", "role": "rebaser", "source": "built-in", "model": None},
                {"slot": "report", "role": "reporter", "source": "built-in", "model": None},
                {"slot": "triage", "role": "triager", "source": "built-in", "model": None},
                {"slot": "rules", "role": "rulewriter", "source": "built-in", "model": None},
                {"slot": "explore", "role": "explorer", "source": "built-in", "model": None},
            ],
        )
