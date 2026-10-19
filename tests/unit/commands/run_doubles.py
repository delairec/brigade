import os
from types import SimpleNamespace

from brigade.adapters.documents import markdown

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


class ProbedClientDouble:
    def __init__(self, probe: dict):
        self.probe = probe

    def answer(self, operation: str, request: dict) -> dict:
        return self.probe


def create_plugin_resolution(probe: dict, forge=None):
    plugins = {"client": ProbedClientDouble(probe), "document": markdown, "forge": forge or SimpleNamespace()}
    return lambda kind, name, **places: plugins[kind]


def spawn_as_this_process(request):
    return SimpleNamespace(pid=os.getpid())
