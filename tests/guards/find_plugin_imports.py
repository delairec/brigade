import ast
from pathlib import Path

from brigade.system.collector_places import BUILT_IN_PACKAGE as COLLECTOR_PACKAGE
from brigade.system.resolve_plugin import (
    BUILT_IN_ENTRY_POINTS,
    BUILT_IN_PLUGIN_PACKAGES,
    CLIENT_ENTRY_POINT,
    CLIENT_PACKAGES,
    COLLECTOR_KIND,
)

PLUGIN_PACKAGES = ("adapters", "collectors", "checks", "outputs")
COMMANDS_PACKAGE = "commands"
COLLECTOR_ENTRY_POINT = "collect"
KIND_PACKAGES = {
    "client": CLIENT_PACKAGES,
    COLLECTOR_KIND: (COLLECTOR_PACKAGE,),
    **{kind: (package,) for kind, package in BUILT_IN_PLUGIN_PACKAGES.items()},
}
ENTRY_POINTS = {"client": CLIENT_ENTRY_POINT, COLLECTOR_KIND: COLLECTOR_ENTRY_POINT, **BUILT_IN_ENTRY_POINTS}


def _name_module(package_root: Path, module_path: Path) -> list[str]:
    parts = [package_root.name, *module_path.relative_to(package_root).with_suffix("").parts]
    if parts[-1] == "__init__":
        return parts[:-1]
    return parts


def _resolve_base(node: ast.ImportFrom, module_parts: list[str], *, is_package: bool) -> str:
    if node.level == 0:
        return node.module
    package_parts = module_parts if is_package else module_parts[:-1]
    anchor = package_parts[: len(package_parts) - (node.level - 1)]
    return ".".join([*anchor, *([node.module] if node.module else [])])


def _imported_names(node: ast.AST, module_parts: list[str], *, is_package: bool) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        base = _resolve_base(node, module_parts, is_package=is_package)
        return [base, *(f"{base}.{alias.name}" for alias in node.names)]
    return []


def _is_within(name: str, package: str) -> bool:
    return name == package or name.startswith(f"{package}.")


def _find_plugin_package(name: str, plugin_packages: list[str]):
    return next((package for package in plugin_packages if _is_within(name, package)), None)


def _find_kind(name: str):
    return next(
        (kind for kind, packages in KIND_PACKAGES.items() if any(_is_within(name, package) for package in packages)),
        None,
    )


def _answers_entry_point(package_root: Path, name: str, kind: str) -> bool:
    module_path = package_root.joinpath(*name.split(".")[1:]).with_suffix(".py")
    if not module_path.is_file():
        return False
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    return any(isinstance(node, ast.FunctionDef) and node.name == ENTRY_POINTS[kind] for node in tree.body)


def _breaks_autonomy(package_root: Path, module_name: str, name: str, plugin_packages: list[str]) -> bool:
    commands_package = f"{package_root.name}.{COMMANDS_PACKAGE}"
    if _find_plugin_package(module_name, plugin_packages) is not None and _is_within(name, commands_package):
        return True
    plugin_package = _find_plugin_package(name, plugin_packages)
    if plugin_package is None:
        return False
    kind = _find_kind(module_name)
    if kind is None:
        return plugin_package != _find_plugin_package(module_name, plugin_packages)
    if _find_kind(name) != kind:
        return True
    return name != module_name and _answers_entry_point(package_root, name, kind)


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    module_parts = _name_module(package_root, module_path)
    is_package = module_path.name == "__init__.py"
    plugin_packages = [f"{package_root.name}.{package}" for package in PLUGIN_PACKAGES]
    module_name = ".".join(module_parts)
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    violations = []
    for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8"))):
        for name in _imported_names(node, module_parts, is_package=is_package):
            if _breaks_autonomy(package_root, module_name, name, plugin_packages):
                violations.append((node.lineno, f"{location}:{node.lineno} imports {name}"))
                break
    return [violation for _, violation in sorted(violations)]


def find_plugin_imports(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        for violation in _inspect_module(package_root, module_path)
    ]
