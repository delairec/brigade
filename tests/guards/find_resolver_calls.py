import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

RESOLVER_NAME = "resolve_plugin"
KIND_RESOLVER_NAMES = ("resolve_collector", "resolve_check")
MODULES_ALLOWED_TO_RESOLVE = ("cli.py", "runtime.py")
PACKAGE_ALLOWED_TO_RESOLVE = "commands"
RESOLVER_MODULE = ("system", "resolve_plugin.py")


def _may_resolve(relative_path: Path) -> bool:
    parts = relative_path.parts
    return parts in ((name,) for name in MODULES_ALLOWED_TO_RESOLVE) or parts[0] == PACKAGE_ALLOWED_TO_RESOLVE


def _name_the_resolver(node: ast.AST, relative_path: Path) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    called = node.func
    if isinstance(called, ast.Attribute):
        return RESOLVER_NAME if called.attr == RESOLVER_NAME else None
    if not isinstance(called, ast.Name):
        return None
    if called.id == RESOLVER_NAME:
        return RESOLVER_NAME
    if called.id in KIND_RESOLVER_NAMES and relative_path.parts != RESOLVER_MODULE:
        return called.id
    return None


def _find_in_module(module: GuardedModule) -> list[Finding]:
    return [
        (node.lineno, node.col_offset, f"calls {name}")
        for node in ast.walk(module.tree)
        if (name := _name_the_resolver(node, module.relative_path)) is not None
    ]


def _is_inspected(relative_path: Path) -> bool:
    return not _may_resolve(relative_path)


def find_resolver_calls(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module, is_inspected=_is_inspected)
