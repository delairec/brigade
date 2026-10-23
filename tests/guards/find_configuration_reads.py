import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

COMMAND_READER = "read_configuration"
READER_NAMES = (COMMAND_READER, "parse_configuration")
READER_MODULES = tuple(("system", f"{name}.py") for name in READER_NAMES)
COMMANDS_PACKAGE = "commands"
PURGE_OF_THE_TRAILS = ("system", "remove_expired_trails.py")
CONFIGURATION_FILE_ATTRIBUTE = "configuration_file"
CONFIGURATION_FILE_CONSTANT = "CONFIGURATION_FILE"
CONFIGURATION_FILE_NAME = "config.toml"
TOML_PARSERS = ("load", "loads")


def _list_allowed_readers(parts: tuple[str, ...]) -> tuple[str, ...]:
    return (COMMAND_READER,) if parts[0] == COMMANDS_PACKAGE else ()


def _name_reader(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    called = node.func
    name = called.attr if isinstance(called, ast.Attribute) else getattr(called, "id", None)
    return name if name in READER_NAMES else None


def _parses_toml(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    owner = node.func.value
    return node.func.attr in TOML_PARSERS and isinstance(owner, ast.Name) and owner.id == "tomllib"


def _names_configuration_file(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == CONFIGURATION_FILE_ATTRIBUTE
    if isinstance(node, ast.Name):
        return node.id == CONFIGURATION_FILE_CONSTANT
    return isinstance(node, ast.Constant) and node.value == CONFIGURATION_FILE_NAME


def _reaches_configuration_file(tree: ast.AST) -> bool:
    return any(_names_configuration_file(node) for node in ast.walk(tree))


def _find_reader_calls(tree: ast.AST, allowed_readers: tuple[str, ...]) -> list[Finding]:
    return [
        (node.lineno, node.col_offset, f"calls {_name_reader(node)}")
        for node in ast.walk(tree)
        if _name_reader(node) is not None and _name_reader(node) not in allowed_readers
    ]


def _find_configuration_parses(tree: ast.AST) -> list[Finding]:
    if not _reaches_configuration_file(tree):
        return []
    return [(node.lineno, node.col_offset, "parses config.toml") for node in ast.walk(tree) if _parses_toml(node)]


def _find_in_module(module: GuardedModule) -> list[Finding]:
    parts = module.relative_path.parts
    findings = _find_reader_calls(module.tree, _list_allowed_readers(parts))
    if parts != PURGE_OF_THE_TRAILS:
        findings = findings + _find_configuration_parses(module.tree)
    return findings


def _is_inspected(relative_path: Path) -> bool:
    return relative_path.parts not in READER_MODULES


def find_configuration_reads(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module, is_inspected=_is_inspected)
