import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
DOUBLE_SUFFIX = "Double"
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _compares_a_sorted_value(node: ast.AST) -> bool:
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "assertEqual"):
        return False
    compared = node.args[0] if node.args else None
    return isinstance(compared, ast.Call) and isinstance(compared.func, ast.Name) and compared.func.id == "sorted"


def _describe_violation(node: ast.AST, function: str) -> str | None:
    if isinstance(node, COMPREHENSIONS):
        return f"projects a value in {function}"
    if _compares_a_sorted_value(node):
        return f"compares a sorted value in {function}"
    return None


def _inspect_node(node: ast.AST, function: str | None) -> list[Finding]:
    if isinstance(node, ast.ClassDef) and node.name.endswith(DOUBLE_SUFFIX):
        return []
    if function is None and isinstance(node, FUNCTIONS):
        function = node.name
    violation = None if function is None else _describe_violation(node, function)
    findings = [] if violation is None else [(node.lineno, 0, violation)]
    for child in ast.iter_child_nodes(node):
        findings.extend(_inspect_node(child, function))
    return findings


def _find_in_module(module: GuardedModule) -> list[Finding]:
    return _inspect_node(module.tree, None)


def find_projections(tests_root: Path) -> list[str]:
    return find_violations(tests_root, _find_in_module, pattern="test_*.py")
