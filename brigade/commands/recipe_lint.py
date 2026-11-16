import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._locate_checkout import locate_checkout
from brigade.commands._locate_recipe_places import locate_recipe_places
from brigade.preflights.locate_preflight import locate_preflight
from brigade.preflights.run_preflight import BUILT_IN_PREFLIGHTS
from brigade.recipes.lint_recipe import RecipeResolvers, lint_recipe
from brigade.recipes.resolve_output import resolve_output
from brigade.recipes.resolve_recipe import resolve_recipe
from brigade.runs.plan_run import SHIPPED_PROCEDURES
from brigade.runs.resolve_procedure import ProcedureDirectories, resolve_procedure
from brigade.runtime import Runtime
from brigade.system.check_shapes import FAILED, OK
from brigade.system.collector_places import locate_collectors
from brigade.system.parse_configuration import SLOTS, Configuration
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.system.resolve_plugin import COLLECTOR_KIND

DOCUMENT_SCHEMA_VERSION = 1
CLIENT_KIND = "client"
EXECUTABLE_ATTRIBUTE = "EXECUTABLE"


def _render_text(document: dict) -> str:
    lines = [f"{document['result']}  recipe {document['recipe']} ({document['source']})"]
    lines.extend(f"  {finding}" for finding in document["findings"])
    return "\n".join(lines)


def _decide_exit_code(document: dict) -> int:
    return int(document["result"] == FAILED)


def _read_client_binary(configuration: Configuration, runtime: Runtime) -> str | None:
    if configuration.client is None:
        return None
    return getattr(runtime.resolve_plugin(CLIENT_KIND, configuration.client), EXECUTABLE_ATTRIBUTE, None)


def _equip_resolvers(project: Path, runtime: Runtime) -> RecipeResolvers:
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    directories = ProcedureDirectories(shipped=SHIPPED_PROCEDURES, instructions=configuration.instructions)
    return RecipeResolvers(
        resolve_collector=lambda name: runtime.resolve_plugin(
            COLLECTOR_KIND, name, places=locate_collectors(project, runtime.paths)
        ),
        resolve_preflight=lambda name: locate_preflight(name, BUILT_IN_PREFLIGHTS),
        resolve_output=lambda name: resolve_output(name, runtime.paths.executable_search_path),
        resolve_procedure=lambda name: resolve_procedure(name, directories),
        slots=SLOTS,
        client_binary=_read_client_binary(configuration, runtime),
    )


def recipe_lint(request: argparse.Namespace, runtime: Runtime) -> dict:
    project = locate_checkout(runtime)
    recipe = resolve_recipe(request.name, locate_recipe_places(project, runtime), runtime.run_process)
    findings = lint_recipe(recipe.document, _equip_resolvers(project, runtime))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "recipe": request.name,
        "source": recipe.source,
        "result": FAILED if findings else OK,
        "findings": findings,
    }


COMMAND = Command(
    path=("recipe", "lint"),
    help="check the recipe named against the schema, its names and its params; exits 1 on a finding",
    arguments=(Argument(("name",), {"help": "the name of the recipe"}),),
    run=recipe_lint,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
