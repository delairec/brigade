import ast
from pathlib import Path

READER_NAMES = ("parse_configuration", "read_optional_configuration", "read_configured_client")
READER_MODULES = tuple(("system", f"{name}.py") for name in READER_NAMES)
PACKAGE_ALLOWED_TO_READ = "commands"
PURGE_OF_THE_TRAILS = ("system", "remove_expired_trails.py")
CONFIGURATION_FILE_ATTRIBUTE = "configuration_file"
CONFIGURATION_FILE_CONSTANT = "CONFIGURATION_FILE"
CONFIGURATION_FILE_NAME = "config.toml"
TOML_PARSERS = ("load", "loads")


def _may_read(parts: tuple[str, ...]) -> bool:
    return parts in READER_MODULES or parts[0] == PACKAGE_ALLOWED_TO_READ


def _name_reader(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    called = node.func
    name = called.attr if isinstance(called, ast.Attribute) else getattr(called, "id", None)
    return name if name in READER_NAMES else None


def _parses_toml(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    owner = node.func.value
    return node.func.attr in TOML_PARSERS and isinstance(owner, ast.Name) and owner.id == "tomllib"


def _names_configuration_file(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == CONFIGURATION_FILE_ATTRIBUTE
    if isinstance(node, ast.Name):
        return node.id == CONFIGURATION_FILE_CONSTANT
    return isinstance(node, ast.Constant) and node.value == CONFIGURATION_FILE_NAME


def _reaches_configuration_file(tree: ast.AST) -> bool:
    return any(_names_configuration_file(node) for node in ast.walk(tree))


def _find_reader_calls(tree: ast.AST) -> list[tuple[int, str]]:
    return [(node.lineno, f"calls {_name_reader(node)}") for node in ast.walk(tree) if _name_reader(node) is not None]


def _find_configuration_parses(tree: ast.AST) -> list[tuple[int, str]]:
    if not _reaches_configuration_file(tree):
        return []
    return [(node.lineno, "parses config.toml") for node in ast.walk(tree) if _parses_toml(node)]


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    parts = module_path.relative_to(package_root).parts
    if _may_read(parts):
        return []
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    findings = _find_reader_calls(tree)
    if parts != PURGE_OF_THE_TRAILS:
        findings = findings + _find_configuration_parses(tree)
    location = Path(package_root.name, *parts).as_posix()
    return [f"{location}:{line} {finding}" for line, finding in sorted(findings)]


def find_configuration_reads(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        for violation in _inspect_module(package_root, module_path)
    ]
