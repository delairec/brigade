import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError, ToolFailure, ToolNotFound
from brigade.roles.resolve_role import ResolvedRole, RoleBindings, resolve_role
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.run_process import ProcessRequest
from brigade.system.trail_writer import TrailWriter

NO_RUNTIME_NEEDED = None
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
        resolved = resolve_role("build", NO_RUNTIME_NEEDED, create_bindings("roles", self.project))

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
            resolve_role("build", NO_RUNTIME_NEEDED, create_bindings("roles", self.project))

        # Assert
        self.assertEqual(str(refusal.exception), f"{unreadable}: has no front matter between two --- lines")


class ResolveRoleOfARolesetDirectoryThatDoesNotExistTest(ResolveRoleTestCase):
    def test_should_fall_through_to_the_built_in_role(self):
        # Arrange
        missing_roleset = str(Path(self.root.name) / "missing-roles")

        # Act
        resolved = resolve_role("build", NO_RUNTIME_NEEDED, create_bindings(missing_roleset))

        # Assert
        self.assertEqual((resolved.role, resolved.source), ("builder", "built-in"))


class ResolveRoleOfASlotNoRoleDeclaresTest(ResolveRoleTestCase):
    def test_should_refuse_naming_the_slot(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_role("deploy", NO_RUNTIME_NEEDED, create_bindings("builtin"))

        # Assert
        self.assertEqual(str(refusal.exception), "no role declares the slot deploy")


class ResolveRoleBoundByNameWhenAwawaAnswersNoAgentTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.config_root = root / "config" / "brigade"
        self.config_root.mkdir(parents=True)
        (self.config_root / "config.toml").write_text(f'instructions = "{root / "instructions"}"\n')
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
            resolve_role("build", self.create_runtime(find_no_awawa), bindings)

        # Assert
        self.assertEqual(str(refusal.exception), "awawa not on PATH")

    def test_should_look_for_the_named_role_in_the_next_source_when_awawa_fails(self):
        # Arrange
        def fail_awawa(request: ProcessRequest):
            raise ToolFailure("awawa show exited 1: no entity @AGENT.planner")

        bindings = create_bindings(None, roles={"build": "planner"})

        # Act
        resolved = resolve_role("build", self.create_runtime(fail_awawa), bindings)

        # Assert
        self.assertEqual((resolved.role, resolved.source), ("planner", "built-in"))
