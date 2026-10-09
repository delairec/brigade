import ast
from pathlib import Path

READER_NAMES = ("read_configuration", "read_optional_configuration", "read_configured_client")
READER_MODULES = tuple(("system", f"{name}.py") for name in READER_NAMES)
PACKAGE_ALLOWED_TO_READ = "commands"


def _may_read(package_root: Path, module_path: Path) -> bool:
    parts = module_path.relative_to(package_root).parts
    return parts in READER_MODULES or parts[0] == PACKAGE_ALLOWED_TO_READ


def _name_reader(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    called = node.func
    name = called.attr if isinstance(called, ast.Attribute) else getattr(called, "id", None)
    return name if name in READER_NAMES else None


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    calls = sorted((node for node in ast.walk(tree) if _name_reader(node) is not None), key=lambda call: call.lineno)
    return [f"{location}:{node.lineno} calls {_name_reader(node)}" for node in calls]


def find_configuration_reads(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        if not _may_read(package_root, module_path)
        for violation in _inspect_module(package_root, module_path)
    ]
