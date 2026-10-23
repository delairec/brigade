import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

RESOLVER_NAME = "resolve_plugin"
MODULES_ALLOWED_TO_RESOLVE = ("cli.py", "runtime.py")
PACKAGE_ALLOWED_TO_RESOLVE = "commands"


def _may_resolve(relative_path: Path) -> bool:
    parts = relative_path.parts
    return parts in ((name,) for name in MODULES_ALLOWED_TO_RESOLVE) or parts[0] == PACKAGE_ALLOWED_TO_RESOLVE


def _names_the_resolver(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    called = node.func
    if isinstance(called, ast.Attribute):
        return called.attr == RESOLVER_NAME
    return isinstance(called, ast.Name) and called.id == RESOLVER_NAME


def _find_in_module(module: GuardedModule) -> list[Finding]:
    return [
        (node.lineno, node.col_offset, f"calls {RESOLVER_NAME}")
        for node in ast.walk(module.tree)
        if _names_the_resolver(node)
    ]


def _is_inspected(relative_path: Path) -> bool:
    return not _may_resolve(relative_path)


def find_resolver_calls(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module, is_inspected=_is_inspected)
