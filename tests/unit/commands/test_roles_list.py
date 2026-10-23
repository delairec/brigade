import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.roles_list import COMMAND
from tests.unit.commands.command_runtime import create_runtime

PROBE_ANSWER = {
    "schema_version": 1,
    "client": "double",
    "version_argv": None,
    "operations": ["probe"],
    "features": [],
    "models": {"standard": "model-standard", "deep": "model-deep"},
}


class ClientDouble:
    def answer(self, operation: str, request: dict) -> dict:
        return PROBE_ANSWER


def _resolve_the_client_double(kind: str, name: str, **places):
    return ClientDouble()


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
        runtime = create_runtime(self.root)

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
        runtime = create_runtime(self.root, resolve_plugin=_resolve_the_client_double)

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document["roles"][1],
            {"slot": "build", "role": "builder", "source": "built-in", "model": "model-standard"},
        )
