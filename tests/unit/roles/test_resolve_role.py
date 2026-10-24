import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError, EntityNotDefined, ToolFailure, ToolNotFound
from brigade.roles.resolve_role import ResolvedRole, RoleBindings, resolve_role
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRecord, ProcessRequest
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NO_RUNTIME_NEEDED = None
NOTHING_CONFIGURED = Configuration()
SHOP_BUILDER = (
    "---\n"
    "name: shopbuilder\n"
    "slot: build\n"
    "work: builds the shop\n"
    "reasoning: light\n"
    "capabilities: read, write, shell\n"
    "budget: 20\n"
    "returns: the branch\n"
    "---\n"
    "You build the shop.\n"
)


def answer_unknown_entity(request: ProcessRequest) -> ProcessRecord:
    return ProcessRecord(
        argv=request.argv,
        cwd=request.cwd,
        exit_code=1,
        stdout="",
        stderr="awawa show: @AGENT.planner is not defined in the workspace\n",
        duration_ms=1,
    )


def create_bindings(roleset: str | None, project_path: Path | None = None, roles: dict | None = None) -> RoleBindings:
    return RoleBindings(project="shop", roles=roles or {}, roleset=roleset, project_path=project_path)


class ResolveRoleTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.project = Path(self.root.name) / "shop"
        self.roleset = self.project / "roles"
        self.roleset.mkdir(parents=True)


class ResolveRoleOfARolesetRelativeToTheProjectTest(ResolveRoleTestCase):
    def test_should_resolve_the_role_file_under_the_project_path(self):
        # Arrange
        (self.roleset / "shopbuilder.md").write_text(SHOP_BUILDER)

        # Act
        resolved = resolve_role("build", NO_RUNTIME_NEEDED, create_bindings("roles", self.project), NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(
            resolved,
            ResolvedRole(
                slot="build",
                role="shopbuilder",
                source="roleset",
                front_matter={
                    "name": "shopbuilder",
                    "slot": "build",
                    "work": "builds the shop",
                    "reasoning": "light",
                    "capabilities": "read, write, shell",
                    "budget": "20",
                    "returns": "the branch",
                },
                body="You build the shop.\n",
            ),
        )

    def test_should_refuse_a_role_file_with_no_front_matter_naming_it(self):
        # Arrange
        unreadable = self.roleset / "notes.md"
        unreadable.write_text("Some notes.\n")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("build", NO_RUNTIME_NEEDED, create_bindings("roles", self.project), NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(str(refusal.exception), f"{unreadable}: has no front matter between two --- lines")


class ResolveRoleOfARolesetDirectoryThatDoesNotExistTest(ResolveRoleTestCase):
    def test_should_fall_through_to_the_built_in_role(self):
        # Arrange
        missing_roleset = str(Path(self.root.name) / "missing-roles")

        # Act
        resolved = resolve_role("build", NO_RUNTIME_NEEDED, create_bindings(missing_roleset), NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(resolved.role, "builder")
        self.assertEqual(resolved.source, "built-in")


class ResolveRoleOfASlotNoRoleDeclaresTest(ResolveRoleTestCase):
    def test_should_refuse_naming_the_slot(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("deploy", NO_RUNTIME_NEEDED, create_bindings("builtin"), NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(str(refusal.exception), "no role declares the slot deploy")


class ResolveRoleBoundByNameWhenAwawaAnswersNoAgentTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.config_root = root / "config"
        self.config_root.mkdir(parents=True)
        self.configuration = Configuration(instructions=str(root / "instructions"))
        self.paths = create_test_paths(root)

    def test_should_let_a_missing_awawa_through_rather_than_look_elsewhere(self):
        # Arrange
        def find_no_awawa(request: ProcessRequest):
            raise ToolNotFound("awawa not on PATH")

        bindings = create_bindings(None, roles={"build": "planner"})

        # Act
        with self.assertRaises(ToolNotFound) as refusal:
            resolve_role(
                "build", create_test_runtime(self.paths, run_process=find_no_awawa), bindings, self.configuration
            )

        # Assert
        self.assertEqual(str(refusal.exception), "awawa not on PATH")

    def test_should_look_for_the_named_role_in_the_next_source_when_awawa_does_not_know_the_entity(self):
        # Arrange
        bindings = create_bindings(None, roles={"build": "planner"})

        # Act
        resolved = resolve_role(
            "build", create_test_runtime(self.paths, run_process=answer_unknown_entity), bindings, self.configuration
        )

        # Assert
        self.assertEqual(resolved.role, "planner")
        self.assertEqual(resolved.source, "built-in")

    def test_should_stop_on_a_failure_of_awawa_show_rather_than_look_elsewhere(self):
        # Arrange
        def fail_awawa(request: ProcessRequest):
            raise ToolFailure("awawa show @AGENT.planner --json /srv/instructions exited 2: awawa: unreadable root")

        bindings = create_bindings(None, roles={"build": "planner"})

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            resolve_role("build", create_test_runtime(self.paths, run_process=fail_awawa), bindings, self.configuration)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "awawa show @AGENT.planner --json /srv/instructions exited 2: awawa: unreadable root",
        )

    def test_should_stop_on_a_failure_of_awawa_context_rather_than_look_elsewhere(self):
        # Arrange
        def fail_awawa_context(request: ProcessRequest) -> ProcessRecord:
            if request.argv[1] == "context":
                raise ToolFailure("awawa context @AGENT.planner exited 2: awawa: unreadable root")
            return _answer_awawa(request)

        bindings = create_bindings(None, roles={"build": "planner"})

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            resolve_role(
                "build", create_test_runtime(self.paths, run_process=fail_awawa_context), bindings, self.configuration
            )

        # Assert
        self.assertEqual(str(refusal.exception), "awawa context @AGENT.planner exited 2: awawa: unreadable root")


PLANNER_FIELDS = [
    {"name": "WORK", "atoms": ['"the plan of a wave"']},
    {"name": "REASONING", "atoms": ["deep"]},
    {"name": "CAPABILITY", "atoms": ["read"]},
    {"name": "CAPABILITY", "atoms": ["shell"]},
    {"name": "BUDGET", "atoms": ["40"]},
    {"name": "RETURNS", "atoms": ['"the plan"']},
]
PLANNER_PACKAGE = 'AGENT planner\n\tWORK "the plan of a wave"\n'


def _answer_awawa(request: ProcessRequest) -> ProcessRecord:
    stdout = json.dumps({"fields": PLANNER_FIELDS}) if request.argv[1] == "show" else PLANNER_PACKAGE
    return ProcessRecord(argv=request.argv, cwd=request.cwd, exit_code=0, stdout=stdout, stderr="", duration_ms=1)


class ResolveRoleBoundByTheSlotsTableTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.instructions = root / "instructions"
        self.paths = create_test_paths(root)

    def test_should_resolve_the_agent_the_configuration_binds_with_no_config_toml_on_disk(self):
        # Arrange
        runtime = create_test_runtime(self.paths, run_process=_answer_awawa)
        configuration = Configuration(instructions=str(self.instructions), slots={"plan": "planner"})
        no_project_bindings = create_bindings(None)

        # Act
        resolved = resolve_role("plan", runtime, no_project_bindings, configuration)

        # Assert
        self.assertEqual(
            resolved,
            ResolvedRole(
                slot="plan",
                role="planner",
                source="instructions",
                front_matter={
                    "name": "planner",
                    "slot": "plan",
                    "work": "the plan of a wave",
                    "reasoning": "deep",
                    "capabilities": "read, shell",
                    "budget": "40",
                    "returns": "the plan",
                },
                body='AGENT planner\n\tWORK "the plan of a wave"\n',
            ),
        )

    def test_should_refuse_an_agent_awawa_does_not_know_naming_it_and_the_corpus(self):
        # Arrange
        configuration = Configuration(instructions=str(self.instructions), slots={"plan": "planner"})
        no_project_bindings = create_bindings(None)

        # Act
        with self.assertRaises(EntityNotDefined) as refusal:
            resolve_role(
                "plan",
                create_test_runtime(self.paths, run_process=answer_unknown_entity),
                no_project_bindings,
                configuration,
            )

        # Assert
        self.assertEqual(str(refusal.exception), f"@AGENT.planner is not defined in {self.instructions}")


class ResolveRoleOfARoleFileWithAnInvalidFrontMatterTest(ResolveRoleTestCase):
    def test_should_refuse_naming_the_file_and_the_key(self):
        # Arrange
        role_file = self.roleset / "shopbuilder.md"
        role_file.write_text(SHOP_BUILDER.replace("reasoning: light", "reasoning: shallow"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("build", NO_RUNTIME_NEEDED, create_bindings(str(self.roleset)), NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(
            str(refusal.exception), f"{role_file}: reasoning is shallow, not one of deepest, deep, standard, light"
        )


class ResolveRoleOfASlotTwoRoleFilesDeclareTest(ResolveRoleTestCase):
    def test_should_refuse_naming_both_files(self):
        # Arrange
        (self.roleset / "a.md").write_text(SHOP_BUILDER)
        (self.roleset / "b.md").write_text(SHOP_BUILDER.replace("name: shopbuilder", "name: otherbuilder"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("build", NO_RUNTIME_NEEDED, create_bindings(str(self.roleset)), NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"slot build is declared by both {self.roleset / 'a.md'} and {self.roleset / 'b.md'}",
        )


class ResolveRoleFromTheCorpusRolesetTest(ResolveRoleTestCase):
    def setUp(self):
        super().setUp()
        self.paths = create_test_paths(self.project)

    def test_should_fall_through_to_the_built_in_role_for_a_slot_the_configuration_leaves_unbound(self):
        # Act
        resolved = resolve_role("build", NO_RUNTIME_NEEDED, create_bindings("corpus"), NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(resolved.source, "built-in")

    def test_should_refuse_a_slot_bound_without_an_instructions_corpus(self):
        # Arrange
        configuration = Configuration(slots={"plan": "planner"})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("plan", create_test_runtime(self.paths), create_bindings("corpus"), configuration)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"slots.plan binds planner but no instructions corpus is set in {self.paths.configuration_file}",
        )

    def test_should_refuse_a_role_the_project_binds_that_no_source_holds(self):
        # Arrange
        bindings = create_bindings("corpus", roles={"build": "nobody"})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("build", NO_RUNTIME_NEEDED, bindings, NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.shop binds build to nobody, a role found nowhere")

    def test_should_refuse_an_agent_whose_fields_break_the_front_matter(self):
        # Arrange
        def answer_shallow_agent(request: ProcessRequest) -> ProcessRecord:
            fields = [{"name": "WORK", "atoms": ['"the plan"']}, {"name": "REASONING", "atoms": ["shallow"]}]
            return ProcessRecord(
                argv=request.argv,
                cwd=request.cwd,
                exit_code=0,
                stdout=json.dumps({"fields": fields}),
                stderr="",
                duration_ms=1,
            )

        configuration = Configuration(instructions=str(self.project / "instructions"), slots={"plan": "planner"})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role(
                "plan",
                create_test_runtime(self.paths, run_process=answer_shallow_agent),
                create_bindings("corpus"),
                configuration,
            )

        # Assert
        self.assertEqual(
            str(refusal.exception), "@AGENT.planner: reasoning is shallow, not one of deepest, deep, standard, light"
        )


MACHINE_PLANNER = (
    "---\n"
    "name: planner\n"
    "slot: plan\n"
    "work: the plan of a wave\n"
    "reasoning: light\n"
    "capabilities: read\n"
    "budget: 20\n"
    "returns: the wave plan\n"
    "---\n"
    "You plan the waves of this machine.\n"
)


class ResolveRoleOfAnAbsoluteRolesetTest(ResolveRoleTestCase):
    def test_should_resolve_the_role_file_of_the_directory_whatever_the_project_path(self):
        # Arrange
        (self.roleset / "shopbuilder.md").write_text(SHOP_BUILDER)
        elsewhere = Path(self.root.name) / "elsewhere"

        # Act
        resolved = resolve_role(
            "build", NO_RUNTIME_NEEDED, create_bindings(str(self.roleset), elsewhere), NOTHING_CONFIGURED
        )

        # Assert
        self.assertEqual(resolved.role, "shopbuilder")
        self.assertEqual(resolved.source, "roleset")


class ResolveRoleFromTheMachineRolesDirectoryTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.machine_roles = root / "config" / "roles"
        self.machine_roles.mkdir(parents=True)
        self.paths = create_test_paths(root)
        self.no_project_bindings = create_bindings(None)

    def test_should_refuse_a_machine_role_file_off_its_keys_naming_the_file_and_the_key(self):
        # Arrange
        role_file = self.machine_roles / "planner.md"
        role_file.write_text(MACHINE_PLANNER.replace("budget: 20\n", "budget: 20\nmodel: opus\n"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("plan", create_test_runtime(self.paths), self.no_project_bindings, NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(str(refusal.exception), f"{role_file}: model names a model")

    def test_should_refuse_two_machine_role_files_declaring_one_slot(self):
        # Arrange
        (self.machine_roles / "a-planner.md").write_text(MACHINE_PLANNER)
        (self.machine_roles / "b-planner.md").write_text(MACHINE_PLANNER)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("plan", create_test_runtime(self.paths), self.no_project_bindings, NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"slot plan is declared by both {self.machine_roles / 'a-planner.md'} and {self.machine_roles / 'b-planner.md'}",
        )

    def test_should_resolve_the_built_in_role_of_a_builtin_roleset_over_the_machine_role_file(self):
        # Arrange
        (self.machine_roles / "planner.md").write_text(MACHINE_PLANNER)

        # Act
        resolved = resolve_role("plan", create_test_runtime(self.paths), create_bindings("builtin"), NOTHING_CONFIGURED)

        # Assert
        self.assertEqual(resolved.role, "planner")
        self.assertEqual(resolved.source, "built-in")

    def test_should_prefer_the_machine_role_file_to_the_agent_entity(self):
        # Arrange
        (self.machine_roles / "planner.md").write_text(MACHINE_PLANNER)
        configuration = Configuration(
            instructions=str(Path(self.root.name) / "instructions"), slots={"plan": "planner"}
        )

        # Act
        resolved = resolve_role("plan", create_test_runtime(self.paths), self.no_project_bindings, configuration)

        # Assert
        self.assertEqual(resolved.source, "machine")


LIGHT_PLANNER_FIELDS = [
    {"name": "WORK", "atoms": ['"the plan of a wave"']},
    {"name": "REASONING", "atoms": ["light"]},
    {"name": "CAPABILITY", "atoms": ["read"]},
    {"name": "BUDGET", "atoms": ["40"]},
    {"name": "RETURNS", "atoms": ['"the plan"']},
]
PLANNER_FIELDS_WITHOUT_A_BUDGET = [
    {"name": "WORK", "atoms": ['"the plan of a wave"']},
    {"name": "REASONING", "atoms": ["deep"]},
    {"name": "CAPABILITY", "atoms": ["read"]},
    {"name": "RETURNS", "atoms": ['"the plan"']},
]
PLANNER_FIELDS_LISTING_TWO_WORKS = [
    {"name": "WORK", "atoms": ['"the plan of a wave"']},
    {"name": "WORK", "atoms": ['"the order of its tasks"']},
    {"name": "REASONING", "atoms": ["deep"]},
    {"name": "CAPABILITY", "atoms": ["read"]},
    {"name": "BUDGET", "atoms": ["40"]},
    {"name": "RETURNS", "atoms": ['"the wave plan"']},
    {"name": "RETURNS", "atoms": ['"the blockers"']},
]


def _create_awawa_answering(fields: list):
    answers = {"show": json.dumps({"fields": fields}), "context": PLANNER_PACKAGE}

    def answer_awawa(request: ProcessRequest) -> ProcessRecord:
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=0, stdout=answers[request.argv[1]], stderr="", duration_ms=1
        )

    return answer_awawa


class ResolveRoleOfAnAgentEntityTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.paths = create_test_paths(root)
        self.configuration = Configuration(instructions=str(root / "instructions"), slots={"plan": "planner"})
        self.no_project_bindings = create_bindings(None)

    def test_should_refuse_an_agent_entity_off_the_role_keys_naming_the_entity_and_the_key(self):
        # Arrange
        runtime = create_test_runtime(self.paths, run_process=_create_awawa_answering(PLANNER_FIELDS_WITHOUT_A_BUDGET))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("plan", runtime, self.no_project_bindings, self.configuration)

        # Assert
        self.assertEqual(str(refusal.exception), "@AGENT.planner: budget is missing")

    def test_should_join_the_values_of_a_field_the_entity_lists_twice(self):
        # Arrange
        runtime = create_test_runtime(self.paths, run_process=_create_awawa_answering(PLANNER_FIELDS_LISTING_TWO_WORKS))

        # Act
        resolved = resolve_role("plan", runtime, self.no_project_bindings, self.configuration)

        # Assert
        self.assertEqual(
            resolved.front_matter,
            {
                "name": "planner",
                "slot": "plan",
                "work": "the plan of a wave; the order of its tasks",
                "reasoning": "deep",
                "capabilities": "read",
                "budget": "40",
                "returns": "the wave plan; the blockers",
            },
        )

    def test_should_read_the_entity_again_at_each_resolution(self):
        # Arrange
        resolve_role(
            "plan",
            create_test_runtime(self.paths, run_process=_create_awawa_answering(PLANNER_FIELDS)),
            self.no_project_bindings,
            self.configuration,
        )
        runtime_reading_a_light_planner = create_test_runtime(
            self.paths, run_process=_create_awawa_answering(LIGHT_PLANNER_FIELDS)
        )

        # Act
        resolved = resolve_role("plan", runtime_reading_a_light_planner, self.no_project_bindings, self.configuration)

        # Assert
        self.assertEqual(resolved.front_matter["reasoning"], "light")
