import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

MOCK_MODULE = "mock"
PATCH = "patch"
PRIVATE_PREFIX = "_"


def _names_the_mock_module(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == MOCK_MODULE
    return isinstance(node, ast.Attribute) and node.attr == MOCK_MODULE


def _describe_violations(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Attribute) and node.attr == PATCH and _names_the_mock_module(node.value):
        return ["patches a name through unittest.mock"]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.module is not None and node.module.endswith(MOCK_MODULE):
        return ["patches a name through unittest.mock" for alias in node.names if alias.name == PATCH]
    return [f"imports the private name {alias.name}" for alias in node.names if alias.name.startswith(PRIVATE_PREFIX)]


def _find_in_module(module: GuardedModule) -> list[Finding]:
    findings = {
        (node.lineno, 0, violation) for node in ast.walk(module.tree) for violation in _describe_violations(node)
    }
    return list(findings)


def find_patches_and_private_imports(tests_root: Path) -> list[str]:
    return find_violations(tests_root, _find_in_module)
