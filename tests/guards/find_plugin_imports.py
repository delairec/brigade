import ast
from pathlib import Path

PLUGIN_PACKAGES = ("adapters", "collectors", "checks", "outputs")


def _name_module(package_root: Path, module_path: Path) -> list[str]:
    parts = [package_root.name, *module_path.relative_to(package_root).with_suffix("").parts]
    if parts[-1] == "__init__":
        return parts[:-1]
    return parts


def _resolve_base(node: ast.ImportFrom, module_parts: list[str], is_package: bool) -> str:
    if node.level == 0:
        return node.module
    package_parts = module_parts if is_package else module_parts[:-1]
    anchor = package_parts[: len(package_parts) - (node.level - 1)]
    return ".".join([*anchor, *([node.module] if node.module else [])])


def _imported_names(node: ast.AST, module_parts: list[str], is_package: bool) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        base = _resolve_base(node, module_parts, is_package)
        return [base, *(f"{base}.{alias.name}" for alias in node.names)]
    return []


def _find_plugin_package(name: str, plugin_packages: list[str]):
    return next((package for package in plugin_packages if name == package or name.startswith(f"{package}.")), None)


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    module_parts = _name_module(package_root, module_path)
    is_package = module_path.name == "__init__.py"
    plugin_packages = [f"{package_root.name}.{package}" for package in PLUGIN_PACKAGES]
    own_package = _find_plugin_package(".".join(module_parts), plugin_packages)
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    violations = []
    for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8"))):
        for name in _imported_names(node, module_parts, is_package):
            plugin_package = _find_plugin_package(name, plugin_packages)
            if plugin_package is not None and plugin_package != own_package:
                violations.append((node.lineno, f"{location}:{node.lineno} imports {name}"))
                break
    return [violation for _, violation in sorted(violations)]


def find_plugin_imports(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        for violation in _inspect_module(package_root, module_path)
    ]
