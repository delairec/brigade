import unittest

from brigade.errors import BrigadeError
from brigade.recipes.lint_recipe import RecipeResolvers, lint_recipe
from tests.unit.recipes.recipe_entity import REVIEW_RECIPE_DOCUMENT


def create_resolver(kind: str, known: str):
    def resolve(name: str) -> None:
        if name != known:
            raise BrigadeError(f"no {kind} {name}")

    return resolve


RESOLVERS = RecipeResolvers(
    resolve_collector=create_resolver("collector", "pull-request"),
    resolve_preflight=create_resolver("preflight", "verify-pull-request"),
    resolve_output=create_resolver("output", "inbox"),
    resolve_procedure=create_resolver("procedure", "verify-pr"),
    slots=("review", "report"),
    client_binary="claude",
)


def create_recipe(steps: list, **keys) -> dict:
    return {
        "schema_version": 1,
        "name": "review",
        "description": "review a pull request",
        "params": ["pr"],
        "max_wall": 30,
        "steps": steps,
        **keys,
    }


class LintRecipeTest(unittest.TestCase):
    def test_should_pass_a_recipe_whose_every_name_resolves_and_every_param_is_declared(self):
        # Act
        findings = lint_recipe(REVIEW_RECIPE_DOCUMENT, RESOLVERS)

        # Assert
        self.assertEqual(findings, [])

    def test_should_refuse_a_recipe_outside_the_schema(self):
        # Arrange
        rows = (
            (
                "a recipe without description",
                {"schema_version": 1, "name": "review", "params": [], "max_wall": 30, "steps": []},
                ["schema: lacks the key description"],
            ),
            (
                "a step of an unknown kind",
                create_recipe([{"kind": "shell", "line": "make"}]),
                [
                    (
                        "schema: steps[0].kind is 'shell', not one of collect, command, gate, judge, output, order,"
                        " corpus, op"
                    )
                ],
            ),
            (
                "a command line in a string",
                create_recipe([{"kind": "command", "argv": "uvx ruff check ."}]),
                ["schema: steps[0]: argv is a string, not a list"],
            ),
            (
                "an op brigade does not run",
                create_recipe([{"kind": "op", "op": "deploy"}]),
                ["schema: steps[0]: op is 'deploy', not one of worktree, commit, pull-request, merge"],
            ),
            (
                "an on_fail outside park, skip, stop and retry:N",
                create_recipe([{"kind": "gate", "preflight": "verify-pull-request", "on_fail": "retry"}]),
                ["schema: steps[0]: on_fail is 'retry', not park, skip, stop or retry:N"],
            ),
            (
                "a key the recipe does not take",
                create_recipe([], timeout=5),
                ["schema: holds the key timeout, which a recipe does not take"],
            ),
            (
                "a gate step holding a check of its own",
                create_recipe([{"kind": "gate", "preflight": "verify-pull-request", "check": "mine"}]),
                ["schema: steps[0]: holds the key check, which a gate step does not take"],
            ),
            (
                "a misspelt on_fail",
                create_recipe([{"kind": "gate", "preflight": "verify-pull-request", "on_fial": "skip"}]),
                ["schema: steps[0]: holds the key on_fial, which a gate step does not take"],
            ),
            (
                "a parameter that is not a text",
                create_recipe([{"kind": "collect", "collector": "pull-request", "parameters": {"limit": 3}}]),
                ["schema: steps[0]: parameters.limit is an integer, not a string"],
            ),
        )
        for title, recipe, expected in rows:
            with self.subTest(title):
                # Act
                findings = lint_recipe(recipe, RESOLVERS)

                # Assert
                self.assertEqual(findings, expected)

    def test_should_pass_a_gate_step_handing_its_preflight_a_declared_param(self):
        # Arrange
        recipe = create_recipe([{"kind": "gate", "preflight": "verify-pull-request", "parameters": {"pr": "{pr}"}}])

        # Act
        findings = lint_recipe(recipe, RESOLVERS)

        # Assert
        self.assertEqual(findings, [])

    def test_should_refuse_a_name_that_does_not_resolve(self):
        # Arrange
        rows = (
            ("a collector", {"kind": "collect", "collector": "issues"}, "steps[0]: no collector issues"),
            ("a preflight", {"kind": "gate", "preflight": "refinement"}, "steps[0]: no preflight refinement"),
            ("an output", {"kind": "output", "output": "slack"}, "steps[0]: no output slack"),
            (
                "a procedure",
                {"kind": "judge", "slot": "review", "procedure": "usage-report", "answer": "REPORT"},
                "steps[0]: no procedure usage-report",
            ),
            (
                "a slot",
                {"kind": "judge", "slot": "deploy", "procedure": "verify-pr", "answer": "REPORT"},
                "steps[0]: no slot deploy: the slots are review, report",
            ),
        )
        for title, step, finding in rows:
            with self.subTest(title):
                # Act
                findings = lint_recipe(create_recipe([step]), RESOLVERS)

                # Assert
                self.assertEqual(findings, [finding])

    def test_should_refuse_a_param_the_recipe_does_not_declare(self):
        # Arrange
        recipe = create_recipe([{"kind": "collect", "collector": "pull-request", "parameters": {"task": "{task}"}}])

        # Act
        findings = lint_recipe(recipe, RESOLVERS)

        # Assert
        self.assertEqual(findings, ["steps[0]: {task} names no param of the recipe"])

    def test_should_refuse_a_client_or_a_model_key(self):
        # Arrange
        rows = (
            (
                "a client key of the recipe",
                create_recipe([], client="claude-code"),
                "the key client names a client or a model, which a recipe never sets",
            ),
            (
                "a model key of a step",
                create_recipe(
                    [{"kind": "judge", "slot": "review", "procedure": "verify-pr", "answer": "R", "model": "opus"}]
                ),
                "steps[0]: the key model names a client or a model, which a recipe never sets",
            ),
        )
        for title, recipe, finding in rows:
            with self.subTest(title):
                # Act
                findings = lint_recipe(recipe, RESOLVERS)

                # Assert
                self.assertEqual(findings, [finding])

    def test_should_refuse_a_command_step_running_the_binary_of_the_configured_client(self):
        # Arrange
        recipe = create_recipe([{"kind": "command", "argv": ["/usr/local/bin/claude", "-p", "review"]}])

        # Act
        findings = lint_recipe(recipe, RESOLVERS)

        # Assert
        self.assertEqual(findings, ["steps[0]: runs claude, the binary of the configured client"])
