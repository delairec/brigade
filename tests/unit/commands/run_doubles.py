import os
from types import SimpleNamespace

from brigade.adapters.documents import markdown
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver

STEP_COUNTING_PROBE = {
    "schema_version": 1,
    "client": "double",
    "version_argv": None,
    "operations": ["probe"],
    "features": ["step_count"],
    "models": {},
}
CLOCK_PROBE = {**STEP_COUNTING_PROBE, "features": []}
CLIENT_AND_DOCUMENT_CONFIGURATION = 'client = "double"\ndocument = "markdown"\n'


def create_plugin_resolution(probe: dict, forge=None):
    return create_plugin_resolver(
        {
            ("client", "double"): ScriptedClient({"probe": probe}),
            ("document", "markdown"): markdown,
            ("forge", "github"): forge or SimpleNamespace(),
        }
    )


def spawn_as_this_process(request):
    return SimpleNamespace(pid=os.getpid())
