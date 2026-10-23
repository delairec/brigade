import ast
from pathlib import Path

MOCK_MODULE = "mock"
PATCH = "patch"
PRIVATE_PREFIX = "_"


def _names_the_mock_module(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == MOCK_MODULE
    return isinstance(node, ast.Attribute) and node.attr == MOCK_MODULE


def _describe_violations(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Attribute) and node.attr == PATCH and _names_the_mock_module(node.value):
        return ["patches through mock.patch"]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.module is not None and node.module.endswith(MOCK_MODULE):
        return ["patches through mock.patch" for alias in node.names if alias.name == PATCH]
    return [f"imports the private name {alias.name}" for alias in node.names if alias.name.startswith(PRIVATE_PREFIX)]


def _inspect_module(tests_root: Path, module_path: Path) -> list[str]:
    location = Path(tests_root.name, module_path.relative_to(tests_root)).as_posix()
    findings = {
        (node.lineno, f"{location}:{node.lineno} {violation}")
        for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
        for violation in _describe_violations(node)
    }
    return [violation for _, violation in sorted(findings)]


def find_patches_and_private_imports(tests_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(tests_root.rglob("*.py"))
        for violation in _inspect_module(tests_root, module_path)
    ]
