import ast
from pathlib import Path

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


def _inspect_method(location: str, method: ast.FunctionDef) -> list[tuple[int, str]]:
    findings = []
    for node in ast.walk(method):
        violation = _describe_violation(node, method.name)
        if violation is not None:
            findings.append((node.lineno, f"{location}:{node.lineno} {violation}"))
    return findings


def _inspect_module(tests_root: Path, module_path: Path) -> list[str]:
    location = Path(tests_root.name, module_path.relative_to(tests_root)).as_posix()
    findings = {
        finding
        for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef) and node.name.startswith(TEST_PREFIX)
        for finding in _inspect_method(location, node)
    }
    return [violation for _, violation in sorted(findings)]


def find_projections(tests_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(tests_root.rglob("*.py"))
        for violation in _inspect_module(tests_root, module_path)
    ]
