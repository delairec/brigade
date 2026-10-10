import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_instructions import TemporaryInstructions
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, REPOSITORY_ROOT, TemporaryMachine

BUILT_IN_ROLES = REPOSITORY_ROOT / "brigade" / "roles" / "data"
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
MACHINE_PLANNER_WITH_AN_ACCENTED_BODY = (
    "---\n"
    "name: planner\n"
    "slot: plan\n"
    "work: the plan of a wave\n"
    "reasoning: light\n"
    "capabilities: read\n"
    "budget: 20\n"
    "returns: the wave plan\n"
    "---\n"
    "Vous planifiez les vagues de cette machine.\n"
    "À chaque tick, une vague au plus.\n"
)
PLANNER_PACKAGE = (
    "AGENT planner\n"
    '\tWORK "the plan of a wave"\n'
    '\tWORK "the order of its tasks"\n'
    "\tREASONING deep\n"
    "\tCAPABILITY read\n"
    "\tCAPABILITY shell\n"
    "\tBUDGET 40\n"
    '\tRETURNS "the wave plan"\n'
    '\tRETURNS "the blockers"\n'
    "\tLOADS @RULE.plans_are_short\n"
    "\n"
    "RULE plans_are_short\n"
    '\tSPEC "a plan fits one screen"\n'
    "\n"
    "// context: 2 entities, 12 lines, depth 2\n"
    "// skip matched no declaration: reasoning\n"
)


def describe_built_in_roles(model_of_deep, model_of_standard, model_of_light) -> list:
    return [
        {"slot": "plan", "role": "planner", "source": "built-in", "model": model_of_deep},
        {"slot": "build", "role": "builder", "source": "built-in", "model": model_of_standard},
        {"slot": "review", "role": "reviewer", "source": "built-in", "model": model_of_deep},
        {"slot": "remediate", "role": "remediator", "source": "built-in", "model": model_of_standard},
        {"slot": "rebase", "role": "rebaser", "source": "built-in", "model": model_of_light},
        {"slot": "report", "role": "reporter", "source": "built-in", "model": model_of_standard},
        {"slot": "triage", "role": "triager", "source": "built-in", "model": model_of_standard},
        {"slot": "rules", "role": "rulewriter", "source": "built-in", "model": model_of_deep},
        {"slot": "explore", "role": "explorer", "source": "built-in", "model": model_of_light},
    ]


class RolesTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))
        self.machine_roles = self.machine.corpus / "roles"

    def tearDown(self):
        self.root.cleanup()

    def run_roles(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "roles", *arguments)

    def write_machine_role(self, file_name: str, content: str) -> Path:
        self.machine_roles.mkdir(parents=True, exist_ok=True)
        role_file = self.machine_roles / file_name
        role_file.write_text(content)
        return role_file


class BrigadeRolesListOnAMachineThatConfiguresNoRoleTest(RolesTestCase):
    def test_should_resolve_every_slot_to_its_built_in_role_with_no_model_bound(self):
        # Arrange
        no_model_bound = None

        # Act
        completed = self.run_roles("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "roles": describe_built_in_roles(no_model_bound, no_model_bound, no_model_bound)},
        )

    def test_should_show_the_model_the_configured_client_adapter_binds(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n[reasoning.light]\nmodel = "haiku"\neffort = "low"\n')

        # Act
        completed = self.run_roles("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "roles": describe_built_in_roles("fable", "opus", "haiku")},
        )

    def test_should_print_the_slots_as_a_table_under_its_header(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

        # Act
        completed = self.run_roles("list")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "slot       role        source    model",
                "plan       planner     built-in  fable",
                "build      builder     built-in  opus",
                "review     reviewer    built-in  fable",
                "remediate  remediator  built-in  opus",
                "rebase     rebaser     built-in  sonnet",
                "report     reporter    built-in  opus",
                "triage     triager     built-in  opus",
                "rules      rulewriter  built-in  fable",
                "explore    explorer    built-in  sonnet",
            ],
        )


class BrigadeRolesShowOfABuiltInRoleTest(RolesTestCase):
    def test_should_print_the_shipped_role_file(self):
        # Act
        completed = self.run_roles("show", "plan")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, (BUILT_IN_ROLES / "planner.md").read_text())

    def test_should_refuse_a_slot_outside_the_nine(self):
        # Act
        completed = self.run_roles("show", "cook")

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertIn("invalid choice: 'cook'", completed.stderr)


class BrigadeRolesFromTheMachineRolesDirectoryTest(RolesTestCase):
    def test_should_resolve_the_slot_a_machine_role_file_declares(self):
        # Arrange
        self.write_machine_role("planner.md", MACHINE_PLANNER)

        # Act
        completed = self.run_roles("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["roles"][0],
            {"slot": "plan", "role": "planner", "source": "machine", "model": None},
        )

    def test_should_print_the_machine_role_file(self):
        # Arrange
        self.write_machine_role("planner.md", MACHINE_PLANNER)

        # Act
        completed = self.run_roles("show", "plan")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, MACHINE_PLANNER)

    def test_should_refuse_a_machine_role_file_off_its_keys_naming_the_file_and_the_key(self):
        # Arrange
        role_file = self.write_machine_role(
            "planner.md", MACHINE_PLANNER.replace("budget: 20\n", "budget: 20\nmodel: opus\n")
        )

        # Act
        completed = self.run_roles("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, f"brigade roles list: {role_file}: model names a model\n")

    def test_should_refuse_two_machine_role_files_declaring_one_slot(self):
        # Arrange
        first = self.write_machine_role("a-planner.md", MACHINE_PLANNER)
        second = self.write_machine_role("b-planner.md", MACHINE_PLANNER)

        # Act
        completed = self.run_roles("show", "plan")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, f"brigade roles show: slot plan is declared by both {first} and {second}\n")


class BrigadeRolesShowShortTest(RolesTestCase):
    def test_should_return_the_front_matter_and_the_size_of_the_body_without_the_body(self):
        # Arrange
        self.write_machine_role("planner.md", MACHINE_PLANNER_WITH_AN_ACCENTED_BODY)

        # Act
        completed = self.run_roles("show", "plan", "--short", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "slot": "plan",
                "role": "planner",
                "source": "machine",
                "front_matter": {
                    "name": "planner",
                    "slot": "plan",
                    "work": "the plan of a wave",
                    "reasoning": "light",
                    "capabilities": "read",
                    "budget": "20",
                    "returns": "the wave plan",
                },
                "body_lines": 2,
                "body_bytes": 79,
            },
        )

    def test_should_print_the_front_matter_block_followed_by_the_size_of_the_body(self):
        # Arrange
        self.write_machine_role("planner.md", MACHINE_PLANNER_WITH_AN_ACCENTED_BODY)

        # Act
        completed = self.run_roles("show", "plan", "--short")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "---\n"
            "name: planner\n"
            "slot: plan\n"
            "work: the plan of a wave\n"
            "reasoning: light\n"
            "capabilities: read\n"
            "budget: 20\n"
            "returns: the wave plan\n"
            "---\n"
            "body: 2 lines, 79 bytes, source machine\n",
        )


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class BrigadeRolesFromTheInstructionsCorpusTest(RolesTestCase):
    def setUp(self):
        super().setUp()
        self.instructions = TemporaryInstructions(Path(self.root.name) / "instructions")
        self.machine.write_configuration(f'instructions = "{self.instructions.root}"\n[slots]\nplan = "planner"\n')

    def test_should_resolve_the_slot_the_slot_table_binds_to_an_agent_entity(self):
        # Act
        completed = self.run_roles("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["roles"][0],
            {"slot": "plan", "role": "planner", "source": "instructions", "model": None},
        )

    def test_should_refuse_an_agent_entity_off_the_role_keys_naming_the_entity_and_the_key(self):
        # Arrange
        self.instructions.write_agents(
            'AGENT planner\n\tWORK "the plan of a wave"\n\tREASONING deep\n\tCAPABILITY read\n'
            '\tRETURNS "the wave plan"\n'
        )

        # Act
        completed = self.run_roles("list")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr), (1, "brigade roles list: @AGENT.planner: budget is missing\n")
        )

    def test_should_leave_an_agent_entity_no_row_names_without_a_slot(self):
        # Act
        completed = self.run_roles("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            [row["role"] for row in json.loads(completed.stdout)["roles"]],
            ["planner", "builder", "reviewer", "remediator", "rebaser", "reporter", "triager", "rulewriter", "explorer"],
        )

    def test_should_fill_the_front_matter_from_the_entity_and_the_body_from_its_package(self):
        # Act
        completed = self.run_roles("show", "plan", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "slot": "plan",
                "role": "planner",
                "source": "instructions",
                "front_matter": {
                    "name": "planner",
                    "slot": "plan",
                    "work": "the plan of a wave; the order of its tasks",
                    "reasoning": "deep",
                    "capabilities": "read, shell",
                    "budget": "40",
                    "returns": "the wave plan; the blockers",
                },
                "body": PLANNER_PACKAGE,
            },
        )

    def test_should_read_the_entity_again_at_each_resolution(self):
        # Arrange
        self.run_roles("show", "plan")
        self.instructions.write_agents(
            'AGENT planner\n\tWORK "the plan of a wave"\n\tREASONING light\n\tCAPABILITY read\n\tBUDGET 40\n\tRETURNS "the wave plan"\n'
        )

        # Act
        completed = self.run_roles("show", "plan", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["front_matter"]["reasoning"], "light")

    def test_should_prefer_the_machine_role_file_to_the_agent_entity(self):
        # Arrange
        self.write_machine_role("planner.md", MACHINE_PLANNER)

        # Act
        completed = self.run_roles("show", "plan", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["source"], "machine")

    def test_should_refuse_a_slot_table_with_no_instructions_corpus_naming_the_key_and_the_file(self):
        # Arrange
        configuration = self.machine.write_configuration('[slots]\nplan = "planner"\n')

        # Act
        completed = self.run_roles("list")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade roles list: slots.plan binds planner but no instructions corpus is set in {configuration}\n",
        )


class BrigadeRolesLintTest(RolesTestCase):
    def test_should_find_the_built_in_role_files_clean(self):
        # Act
        completed = self.run_roles("lint", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "files": [
                    "brigade/roles/data/builder.md",
                    "brigade/roles/data/explorer.md",
                    "brigade/roles/data/planner.md",
                    "brigade/roles/data/rebaser.md",
                    "brigade/roles/data/remediator.md",
                    "brigade/roles/data/reporter.md",
                    "brigade/roles/data/reviewer.md",
                    "brigade/roles/data/rulewriter.md",
                    "brigade/roles/data/triager.md",
                ],
                "findings": [],
            },
        )

    def test_should_fail_naming_the_file_and_the_key_of_a_role_file_off_its_declaration(self):
        rows = [
            (
                "a model named",
                MACHINE_PLANNER.replace("budget: 20\n", "budget: 20\nmodel: opus\n"),
                "model",
                "names a model",
            ),
            (
                "a declared key missing",
                MACHINE_PLANNER.replace("returns: the wave plan\n", ""),
                "returns",
                "is missing",
            ),
            (
                "an unknown key",
                MACHINE_PLANNER.replace("budget: 20\n", "budget: 20\ncolour: blue\n"),
                "colour",
                "is not a declared key",
            ),
            (
                "a value outside its set",
                MACHINE_PLANNER.replace("reasoning: light\n", "reasoning: huge\n"),
                "reasoning",
                "is huge, not one of deepest, deep, standard, light",
            ),
            ("no front matter", "You plan.\n", None, "has no front matter between two --- lines"),
        ]
        for case, content, expected_key, expected_problem in rows:
            with self.subTest(case=case):
                # Arrange
                role_file = self.write_machine_role("planner.md", content)

                # Act
                completed = self.run_roles("lint", "--json")

                # Assert
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout)["findings"],
                    [{"file": str(role_file), "key": expected_key, "problem": expected_problem}],
                )

    def test_should_find_a_slot_two_machine_role_files_declare(self):
        # Arrange
        first = self.write_machine_role("a-planner.md", MACHINE_PLANNER)
        second = self.write_machine_role("b-planner.md", MACHINE_PLANNER)

        # Act
        completed = self.run_roles("lint", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["findings"],
            [{"file": str(second), "key": "slot", "problem": f"plan is also declared by {first}"}],
        )

    def test_should_find_no_shared_slot_between_two_machine_role_files_declaring_none(self):
        # Arrange
        planner_without_slot = MACHINE_PLANNER.replace("slot: plan\n", "")
        first = self.write_machine_role("a-planner.md", planner_without_slot)
        second = self.write_machine_role("b-planner.md", planner_without_slot)

        # Act
        completed = self.run_roles("lint", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["findings"],
            [
                {"file": str(first), "key": "slot", "problem": "is missing"},
                {"file": str(second), "key": "slot", "problem": "is missing"},
            ],
        )

    def test_should_print_each_finding_and_the_count_as_text(self):
        # Arrange
        role_file = self.write_machine_role(
            "planner.md", MACHINE_PLANNER.replace("budget: 20\n", "budget: 20\nmodel: opus\n")
        )

        # Act
        completed = self.run_roles("lint")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(), [f"{role_file}: model names a model", "", "roles lint: 10 files, 1 finding"]
        )
