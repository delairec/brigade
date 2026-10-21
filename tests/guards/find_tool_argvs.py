import ast
from pathlib import Path

GUARDED_TOOLS = ("awawa", "git")
GATEWAY_PACKAGES = ("corpus", "git")


def _opened_tool(node: ast.AST) -> str | None:
    if not isinstance(node, (ast.Tuple, ast.List)) or not node.elts:
        return None
    first = node.elts[0]
    if isinstance(first, ast.Constant) and first.value in GUARDED_TOOLS:
        return first.value
    return None


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    findings = []
    for node in ast.walk(tree):
        tool = _opened_tool(node)
        if tool:
            findings.append(
                (node.lineno, node.col_offset, f"{location}:{node.lineno} builds an argv opening on {tool}")
            )
    return [violation for _, _, violation in sorted(findings)]


def find_tool_argvs(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        if module_path.relative_to(package_root).parts[0] not in GATEWAY_PACKAGES
        for violation in _inspect_module(package_root, module_path)
    ]
