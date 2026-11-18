import os

from brigade.adapters.documents import markdown
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver
from tests.unit.create_preflight_plugins import resolve_preflight_kinds_or
from tests.unit.plugin_double import PluginDouble
from tests.unit.spawned_process_double import SpawnedProcessDouble

TURN_COUNTING_PROBE = {
    "schema_version": 1,
    "client": "double",
    "version_argv": None,
    "operations": ["probe"],
    "features": ["turn_count"],
    "models": {},
}
CLOCK_PROBE = {**TURN_COUNTING_PROBE, "features": []}
CLIENT_AND_DOCUMENT_CONFIGURATION = 'client = "double"\nprogress_form = "markdown"\n'


def create_plugin_resolution(probe: dict, forge=None):
    return resolve_preflight_kinds_or(
        create_plugin_resolver(
            {
                ("client", "double"): ScriptedClient({"probe": probe}),
                ("client", "fake"): ScriptedClient({"probe": probe}),
                ("progress_form", "markdown"): markdown,
                ("forge", "github"): forge or PluginDouble(kind="forge", name="github"),
            }
        )
    )


def spawn_as_this_process(request):
    return SpawnedProcessDouble(pid=os.getpid())
