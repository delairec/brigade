import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

MODULES_ALLOWED_TO_READ = ("system/paths.py", "launcher.py")
OS_READS = ("environ", "getenv")
EXPANDUSER = "expanduser"


def _describe_attribute_read(node: ast.Attribute):
    if isinstance(node.value, ast.Name) and node.value.id == "os" and node.attr in OS_READS:
        return f"os.{node.attr}"
    if node.attr == "home" and isinstance(node.value, (ast.Name, ast.Attribute)):
        owner = node.value.id if isinstance(node.value, ast.Name) else node.value.attr
        if owner == "Path":
            return "Path.home"
    if node.attr == EXPANDUSER:
        return EXPANDUSER
    return None


def _describe_import_reads(node: ast.ImportFrom) -> list[str]:
    if node.module == "os":
        return [f"os.{alias.name}" for alias in node.names if alias.name in OS_READS]
    if node.module in ("os.path", "posixpath"):
        return [EXPANDUSER for alias in node.names if alias.name == EXPANDUSER]
    return []


def _describe_reads(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Attribute):
        read = _describe_attribute_read(node)
        return [] if read is None else [read]
    if isinstance(node, ast.ImportFrom):
        return _describe_import_reads(node)
    return []


def _find_in_module(module: GuardedModule) -> list[Finding]:
    return [
        (node.lineno, node.col_offset, f"reads {read}")
        for node in ast.walk(module.tree)
        for read in _describe_reads(node)
    ]


def _is_inspected(relative_path: Path) -> bool:
    return relative_path.as_posix() not in MODULES_ALLOWED_TO_READ


def find_environment_reads(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module, is_inspected=_is_inspected)
