import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

SUBPROCESS_MODULE = "subprocess"
LAUNCHING_FUNCTIONS = ("run", "Popen")
MODULE_ALLOWED_TO_LAUNCH = Path("process_launcher.py")


def _names_bound_to_subprocess(tree: ast.AST) -> set[str]:
    return {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == SUBPROCESS_MODULE
    }


def _launch_of(node: ast.AST, subprocess_names: set[str]) -> str | None:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in subprocess_names
        and node.func.attr in LAUNCHING_FUNCTIONS
    ):
        return f"launches {SUBPROCESS_MODULE}.{node.func.attr}"
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == SUBPROCESS_MODULE:
        imported = [alias.name for alias in node.names if alias.name in LAUNCHING_FUNCTIONS]
        if imported:
            return f"imports {SUBPROCESS_MODULE}.{imported[0]}"
    return None


def _find_in_module(module: GuardedModule) -> list[Finding]:
    subprocess_names = _names_bound_to_subprocess(module.tree)
    findings = []
    for node in ast.walk(module.tree):
        launch = _launch_of(node, subprocess_names)
        if launch:
            findings.append((node.lineno, node.col_offset, launch))
    return findings


def _is_inspected(relative_path: Path) -> bool:
    return relative_path != MODULE_ALLOWED_TO_LAUNCH


def find_subprocess_launches(tests_root: Path) -> list[str]:
    return find_violations(tests_root, _find_in_module, is_inspected=_is_inspected)
