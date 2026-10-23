import ast
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GuardedModule:
    root: Path
    relative_path: Path
    source: str
    tree: ast.Module


Finding = tuple[int, int, str]


def _inspect_every_module(relative_path: Path) -> bool:
    return True


def _inspect_module(
    root: Path, module_path: Path, find_in_module: Callable[[GuardedModule], list[Finding]]
) -> list[str]:
    relative_path = module_path.relative_to(root)
    source = module_path.read_text(encoding="utf-8")
    findings = find_in_module(GuardedModule(root, relative_path, source, ast.parse(source)))
    location = Path(root.name, relative_path).as_posix()
    return [f"{location}:{line} {description}" for line, _, description in sorted(findings)]


def find_violations(
    root: Path,
    find_in_module: Callable[[GuardedModule], list[Finding]],
    is_inspected: Callable[[Path], bool] = _inspect_every_module,
    pattern: str = "*.py",
) -> list[str]:
    return [
        violation
        for module_path in sorted(root.rglob(pattern))
        if is_inspected(module_path.relative_to(root))
        for violation in _inspect_module(root, module_path, find_in_module)
    ]
