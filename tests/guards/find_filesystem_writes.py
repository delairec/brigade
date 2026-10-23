import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

PACKAGE_ALLOWED_TO_WRITE = "system"
WRITING_METHODS = ("write_text", "write_bytes", "mkdir", "rename")
WRITING_FUNCTIONS = {("os", "rename"), ("os", "replace"), ("shutil", "rmtree"), ("tempfile", "mkdtemp")}
WRITING_MODE_LETTERS = frozenset("wax+")


def _imported_functions(tree: ast.AST) -> dict[str, str]:
    return {
        alias.asname or alias.name: f"{node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
        for alias in node.names
        if (node.module, alias.name) in WRITING_FUNCTIONS
    }


def _opening_mode(call: ast.Call, mode_position: int) -> ast.expr | None:
    keyword_mode = next((keyword.value for keyword in call.keywords if keyword.arg == "mode"), None)
    if keyword_mode is not None:
        return keyword_mode
    return call.args[mode_position] if len(call.args) > mode_position else None


def _opens_for_writing(call: ast.Call, mode_position: int) -> bool:
    mode = _opening_mode(call, mode_position)
    return (
        isinstance(mode, ast.Constant) and isinstance(mode.value, str) and bool(WRITING_MODE_LETTERS & set(mode.value))
    )


def _replaces_a_path(call: ast.Call) -> bool:
    return len(call.args) == 1 and not call.keywords


def _name_write(call: ast.Call, imported: dict[str, str]) -> str | None:
    function = call.func
    if isinstance(function, ast.Name):
        if function.id == "open" and _opens_for_writing(call, 1):
            return "open"
        return imported.get(function.id)
    if not isinstance(function, ast.Attribute):
        return None
    if isinstance(function.value, ast.Name) and (function.value.id, function.attr) in WRITING_FUNCTIONS:
        return f"{function.value.id}.{function.attr}"
    if function.attr == "open" and _opens_for_writing(call, 0):
        return "open"
    if function.attr in WRITING_METHODS or (function.attr == "replace" and _replaces_a_path(call)):
        return function.attr
    return None


def _find_in_module(module: GuardedModule) -> list[Finding]:
    imported = _imported_functions(module.tree)
    findings = []
    for node in ast.walk(module.tree):
        write = _name_write(node, imported) if isinstance(node, ast.Call) else None
        if write:
            findings.append((node.lineno, node.col_offset, f"writes through {write}"))
    return findings


def _is_inspected(relative_path: Path) -> bool:
    return relative_path.parts[0] != PACKAGE_ALLOWED_TO_WRITE


def find_filesystem_writes(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module, is_inspected=_is_inspected)
