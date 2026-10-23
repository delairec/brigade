import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError, EntityNotDefined, ToolFailure, ToolNotFound
from brigade.roles.resolve_role import ResolvedRole, RoleBindings, resolve_role
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.read_configuration import Configuration
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.system.trail_writer import TrailWriter

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


def _refuse_spawn(request):
    raise AssertionError(f"resolve_role spawned {request.argv}")


def _refuse_resolution(kind: str, name: str):
    raise AssertionError(f"resolve_role resolved the {kind} plugin {name}")


def _keep_no_trace(trace) -> None:
    pass


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
        self.assertEqual((resolved.role, resolved.source), ("builder", "built-in"))


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
        self.config_root = root / "config" / "brigade"
        self.config_root.mkdir(parents=True)
        self.configuration = Configuration(instructions=str(root / "instructions"))
        self.paths = Paths(
            config_root=self.config_root,
            state_root=root / "state" / "brigade",
            cache_root=root / "cache" / "brigade",
            home=root,
            executable_search_path="",
        )

    def create_runtime(self, run_process) -> Runtime:
        return Runtime(
            run_process=run_process,
            spawn_process=_refuse_spawn,
            paths=self.paths,
            now=datetime(2026, 10, 7, 9, 0, tzinfo=UTC),
            read_clock=lambda: datetime(2026, 10, 7, 9, 0, tzinfo=UTC),
            read_monotonic=lambda: 0.0,
            entry_point=Path("/srv/brigade/bin/brigade"),
            trail=TrailWriter(_keep_no_trace),
            resolve_plugin=_refuse_resolution,
        )

    def test_should_let_a_missing_awawa_through_rather_than_look_elsewhere(self):
        # Arrange
        def find_no_awawa(request: ProcessRequest):
            raise ToolNotFound("awawa not on PATH")

        bindings = create_bindings(None, roles={"build": "planner"})

        # Act
        with self.assertRaises(ToolNotFound) as refusal:
            resolve_role("build", self.create_runtime(find_no_awawa), bindings, self.configuration)

        # Assert
        self.assertEqual(str(refusal.exception), "awawa not on PATH")

    def test_should_look_for_the_named_role_in_the_next_source_when_awawa_does_not_know_the_entity(self):
        # Arrange
        def answer_unknown_entity(request: ProcessRequest) -> ProcessRecord:
            return ProcessRecord(
                argv=request.argv,
                cwd=request.cwd,
                exit_code=1,
                stdout="",
                stderr="awawa show: @AGENT.planner is not defined in the workspace\n",
                duration_ms=1,
            )

        bindings = create_bindings(None, roles={"build": "planner"})

        # Act
        resolved = resolve_role("build", self.create_runtime(answer_unknown_entity), bindings, self.configuration)

        # Assert
        self.assertEqual((resolved.role, resolved.source), ("planner", "built-in"))

    def test_should_stop_on_a_failure_of_awawa_show_rather_than_look_elsewhere(self):
        # Arrange
        def fail_awawa(request: ProcessRequest):
            raise ToolFailure("awawa show @AGENT.planner --json /srv/instructions exited 2: awawa: unreadable root")

        bindings = create_bindings(None, roles={"build": "planner"})

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            resolve_role("build", self.create_runtime(fail_awawa), bindings, self.configuration)

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
            resolve_role("build", self.create_runtime(fail_awawa_context), bindings, self.configuration)

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
        self.paths = Paths(
            config_root=root / "config" / "brigade",
            state_root=root / "state" / "brigade",
            cache_root=root / "cache" / "brigade",
            home=root,
            executable_search_path="",
        )

    def create_runtime(self, run_process) -> Runtime:
        return Runtime(
            run_process=run_process,
            spawn_process=_refuse_spawn,
            paths=self.paths,
            now=datetime(2026, 10, 9, 9, 0, tzinfo=UTC),
            read_clock=lambda: datetime(2026, 10, 9, 9, 0, tzinfo=UTC),
            read_monotonic=lambda: 0.0,
            entry_point=Path("/srv/brigade/bin/brigade"),
            trail=TrailWriter(_keep_no_trace),
            resolve_plugin=_refuse_resolution,
        )

    def test_should_resolve_the_agent_the_configuration_binds_with_no_config_toml_on_disk(self):
        # Arrange
        runtime = self.create_runtime(_answer_awawa)
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
        def answer_unknown_entity(request: ProcessRequest) -> ProcessRecord:
            return ProcessRecord(
                argv=request.argv,
                cwd=request.cwd,
                exit_code=1,
                stdout="",
                stderr="awawa show: @AGENT.planner is not defined in the workspace\n",
                duration_ms=1,
            )

        configuration = Configuration(instructions=str(self.instructions), slots={"plan": "planner"})
        no_project_bindings = create_bindings(None)

        # Act
        with self.assertRaises(EntityNotDefined) as refusal:
            resolve_role("plan", self.create_runtime(answer_unknown_entity), no_project_bindings, configuration)

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
        self.paths = Paths(
            config_root=self.project / "config",
            state_root=self.project / "state",
            cache_root=self.project / "cache",
            home=self.project,
            executable_search_path="",
        )

    def create_runtime(self, run_process) -> Runtime:
        return Runtime(
            run_process=run_process,
            spawn_process=_refuse_spawn,
            paths=self.paths,
            now=datetime(2026, 10, 19, 9, 0, tzinfo=UTC),
            read_clock=lambda: datetime(2026, 10, 19, 9, 0, tzinfo=UTC),
            read_monotonic=lambda: 0.0,
            entry_point=Path("/srv/brigade/bin/brigade"),
            trail=TrailWriter(_keep_no_trace),
            resolve_plugin=_refuse_resolution,
        )

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
            resolve_role("plan", self.create_runtime(None), create_bindings("corpus"), configuration)

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
            resolve_role("plan", self.create_runtime(answer_shallow_agent), create_bindings("corpus"), configuration)

        # Assert
        self.assertEqual(
            str(refusal.exception), "@AGENT.planner: reasoning is shallow, not one of deepest, deep, standard, light"
        )
