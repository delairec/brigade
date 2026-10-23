import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

STAND_IN = "SimpleNamespace"
FIXTURE_MODULES = {
    "ForgeDouble": Path("unit/forge_double.py"),
    "RepositoryTestCase": Path("integration/repository_test_case.py"),
    "IDENTITY": Path("integration/repository_test_case.py"),
    "try_lock": Path("unit/system/try_lock.py"),
    "signal_itself": Path("unit/system/signal_itself.py"),
    "_inspect_module": Path("guards/find_violations.py"),
}


def _read_referenced_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.ImportFrom):
        return next((alias.name for alias in node.names if alias.name == STAND_IN), None)
    return None


def _read_declared_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.ClassDef | ast.FunctionDef):
        return [node.name]
    if isinstance(node, ast.Assign):
        return [target.id for target in node.targets if isinstance(target, ast.Name)]
    return []


def _find_stand_ins(module: GuardedModule) -> list[Finding]:
    return [
        (node.lineno, node.col_offset, f"{STAND_IN} stands in for the record or the double it imitates")
        for node in ast.walk(module.tree)
        if _read_referenced_name(node) == STAND_IN
    ]


def _find_redeclarations(module: GuardedModule) -> list[Finding]:
    return [
        (node.lineno, node.col_offset, f"{name} is declared again, its declaration being tests/{fixture_module}")
        for node in ast.walk(module.tree)
        for name in _read_declared_names(node)
        if (fixture_module := FIXTURE_MODULES.get(name)) and fixture_module != module.relative_path
    ]


def _find_in_module(module: GuardedModule) -> list[Finding]:
    return _find_stand_ins(module) + _find_redeclarations(module)


def find_fixture_redeclarations(tests_root: Path) -> list[str]:
    return find_violations(tests_root, _find_in_module)
