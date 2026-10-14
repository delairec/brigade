import ast
from pathlib import Path

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


def _inspect_module(tests_root: Path, module_path: Path) -> list[str]:
    location = Path(tests_root.name, module_path.relative_to(tests_root)).as_posix()
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    subprocess_names = _names_bound_to_subprocess(tree)
    findings = []
    for node in ast.walk(tree):
        launch = _launch_of(node, subprocess_names)
        if launch:
            findings.append((node.lineno, node.col_offset, f"{location}:{node.lineno} {launch}"))
    return [violation for _, _, violation in sorted(findings)]


def find_subprocess_launches(tests_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(tests_root.rglob("*.py"))
        if module_path.relative_to(tests_root) != MODULE_ALLOWED_TO_LAUNCH
        for violation in _inspect_module(tests_root, module_path)
    ]
