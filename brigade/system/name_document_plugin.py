from pathlib import Path

from brigade.errors import BrigadeError

DOCUMENT_PLUGINS_BY_EXTENSION = {".md": "markdown", ".awawa": "awawa"}
EXTENSIONS_BY_DOCUMENT_PLUGIN = {plugin: extension for extension, plugin in DOCUMENT_PLUGINS_BY_EXTENSION.items()}


def name_document_plugin(path: Path) -> str:
    plugin = DOCUMENT_PLUGINS_BY_EXTENSION.get(path.suffix)
    if plugin is None:
        raise BrigadeError(f"no document plugin reads {path}")
    return plugin
