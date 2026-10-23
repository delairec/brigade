import ast
from pathlib import Path


def _compares_a_packed_tuple(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "assertEqual"
        and bool(node.args)
        and isinstance(node.args[0], ast.Tuple)
    )


def _inspect_module(tests_root: Path, module_path: Path) -> list[str]:
    location = Path(tests_root.name, module_path.relative_to(tests_root)).as_posix()
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    lines = sorted({node.lineno for node in ast.walk(tree) if _compares_a_packed_tuple(node)})
    return [f"{location}:{line} compares a packed tuple" for line in lines]


def find_packed_tuples(tests_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(tests_root.rglob("*.py"))
        for violation in _inspect_module(tests_root, module_path)
    ]
