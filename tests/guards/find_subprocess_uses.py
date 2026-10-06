import ast
from pathlib import Path

SUBPROCESS_MODULE = "subprocess"
PACKAGE_ALLOWED_TO_IMPORT = "system"


def _is_in_allowed_package(package_root: Path, module_path: Path) -> bool:
    return module_path.relative_to(package_root).parts[0] == PACKAGE_ALLOWED_TO_IMPORT


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
        if keyword.arg == "shell"
        and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
    ]


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    may_import = _is_in_allowed_package(package_root, module_path)
    findings = []
    for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8"))):
        if not may_import and _imports_subprocess(node):
            findings.append((node.lineno, node.col_offset, f"{location}:{node.lineno} imports subprocess"))
        for keyword in _shell_keywords(node):
            findings.append(
                (keyword.lineno, keyword.col_offset, f"{location}:{keyword.lineno} passes shell={ast.unparse(keyword.value)}")
            )
    return [violation for _, _, violation in sorted(findings)]


def find_subprocess_uses(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        for violation in _inspect_module(package_root, module_path)
    ]
