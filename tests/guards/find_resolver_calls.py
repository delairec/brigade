import ast
from pathlib import Path

RESOLVER_NAME = "resolve_plugin"
MODULES_ALLOWED_TO_RESOLVE = ("cli.py", "runtime.py")
PACKAGE_ALLOWED_TO_RESOLVE = "commands"


def _may_resolve(package_root: Path, module_path: Path) -> bool:
    parts = module_path.relative_to(package_root).parts
    return parts in ((name,) for name in MODULES_ALLOWED_TO_RESOLVE) or parts[0] == PACKAGE_ALLOWED_TO_RESOLVE


def _names_the_resolver(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    called = node.func
    if isinstance(called, ast.Attribute):
        return called.attr == RESOLVER_NAME
    return isinstance(called, ast.Name) and called.id == RESOLVER_NAME


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    calls = [node for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8"))) if _names_the_resolver(node)]
    return [f"{location}:{node.lineno} calls {RESOLVER_NAME}" for node in sorted(calls, key=lambda call: call.lineno)]


def find_resolver_calls(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        if not _may_resolve(package_root, module_path)
        for violation in _inspect_module(package_root, module_path)
    ]
