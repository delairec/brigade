import ast
from pathlib import Path

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


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    findings = [
        (node.lineno, node.col_offset, f"{location}:{node.lineno} reads {read}")
        for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
        for read in _describe_reads(node)
    ]
    return [violation for _, _, violation in sorted(findings)]


def find_environment_reads(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        if module_path.relative_to(package_root).as_posix() not in MODULES_ALLOWED_TO_READ
        for violation in _inspect_module(package_root, module_path)
    ]
