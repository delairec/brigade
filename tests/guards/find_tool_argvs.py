import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

GUARDED_TOOLS = ("awawa", "git")
GATEWAY_PACKAGES = ("corpus", "git")


def _opened_tool(node: ast.AST) -> str | None:
    if not isinstance(node, (ast.Tuple, ast.List)) or not node.elts:
        return None
    first = node.elts[0]
    if isinstance(first, ast.Constant) and first.value in GUARDED_TOOLS:
        return first.value
    return None


def _find_in_module(module: GuardedModule) -> list[Finding]:
    findings = []
    for node in ast.walk(module.tree):
        tool = _opened_tool(node)
        if tool:
            findings.append((node.lineno, node.col_offset, f"builds an argv opening on {tool}"))
    return findings


def _is_inspected(relative_path: Path) -> bool:
    return relative_path.parts[0] not in GATEWAY_PACKAGES


def find_tool_argvs(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module, is_inspected=_is_inspected)
