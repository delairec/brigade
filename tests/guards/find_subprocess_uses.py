import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

SUBPROCESS_MODULE = "subprocess"
PACKAGE_ALLOWED_TO_IMPORT = "system"


def _imports_subprocess(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(alias.name == SUBPROCESS_MODULE for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.level == 0 and node.module == SUBPROCESS_MODULE
    return False


def _shell_keywords(node: ast.AST) -> list[ast.keyword]:
    if not isinstance(node, ast.Call):
        return []
    return [
        keyword
        for keyword in node.keywords
        if keyword.arg == "shell" and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
    ]


def _find_in_module(module: GuardedModule) -> list[Finding]:
    may_import = module.relative_path.parts[0] == PACKAGE_ALLOWED_TO_IMPORT
    findings = []
    for node in ast.walk(module.tree):
        if not may_import and _imports_subprocess(node):
            findings.append((node.lineno, node.col_offset, "imports subprocess"))
        findings.extend(
            (keyword.lineno, keyword.col_offset, f"passes shell={ast.unparse(keyword.value)}")
            for keyword in _shell_keywords(node)
        )
    return findings


def find_subprocess_uses(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module)
