import ast
from pathlib import Path


def _read_titles(suite_root: Path) -> set[str]:
    return {
        node.name
        for module_path in suite_root.rglob("test_*.py")
        for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test")
    }


def find_shared_titles(tests_root: Path) -> list[str]:
    shared = _read_titles(tests_root / "unit") & _read_titles(tests_root / "cli")
    return [f"{title} is tested in tests/unit and in tests/cli" for title in sorted(shared)]
