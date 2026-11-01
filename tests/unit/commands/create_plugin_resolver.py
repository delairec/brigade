from collections.abc import Callable


class ScriptedClient:
    def __init__(self, answers: dict):
        self.answers = answers

    def answer(self, operation: str, request: dict) -> dict:
        return self.answers[operation]


def create_plugin_resolver(plugins: dict) -> Callable:
    def resolve_plugin(kind: str, name: str, **options):
        if (kind, name) not in plugins:
            raise AssertionError(f"the command resolved the {kind} plugin {name}")
        plugin = plugins[kind, name]
        if isinstance(plugin, Exception):
            raise plugin
        return plugin

    return resolve_plugin
