import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations


def _compares_a_packed_tuple(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "assertEqual"
        and bool(node.args)
        and isinstance(node.args[0], ast.Tuple)
    )


def _find_in_module(module: GuardedModule) -> list[Finding]:
    lines = {node.lineno for node in ast.walk(module.tree) if _compares_a_packed_tuple(node)}
    return [(line, 0, "compares a packed tuple") for line in lines]


def find_packed_tuples(tests_root: Path) -> list[str]:
    return find_violations(tests_root, _find_in_module)
