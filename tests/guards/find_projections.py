import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
TEST_PREFIX = "test"


def _compares_a_sorted_value(node: ast.AST) -> bool:
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "assertEqual"):
        return False
    compared = node.args[0] if node.args else None
    return isinstance(compared, ast.Call) and isinstance(compared.func, ast.Name) and compared.func.id == "sorted"


def _describe_violation(node: ast.AST, method: str) -> str | None:
    if isinstance(node, COMPREHENSIONS):
        return f"projects a value in {method}"
    if _compares_a_sorted_value(node):
        return f"compares a sorted value in {method}"
    return None


def _inspect_method(method: ast.FunctionDef) -> list[Finding]:
    findings = []
    for node in ast.walk(method):
        violation = _describe_violation(node, method.name)
        if violation is not None:
            findings.append((node.lineno, 0, violation))
    return findings


def _find_in_module(module: GuardedModule) -> list[Finding]:
    findings = {
        finding
        for node in ast.walk(module.tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith(TEST_PREFIX)
        for finding in _inspect_method(node)
    }
    return list(findings)


def find_projections(tests_root: Path) -> list[str]:
    return find_violations(tests_root, _find_in_module)
