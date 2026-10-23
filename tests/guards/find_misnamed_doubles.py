import ast
from pathlib import Path

ACCEPTED_SUFFIXES = ("Test", "TestCase", "Double", "Arrangement")


def _find_misnamed_classes(tests_root: Path, module_path: Path) -> list[str]:
    location = Path(tests_root.name, module_path.relative_to(tests_root)).as_posix()
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    return [
        f"{location}:{node.lineno} {node.name} lacks the Double suffix"
        for node in tree.body
        if isinstance(node, ast.ClassDef) and not node.name.endswith(ACCEPTED_SUFFIXES)
    ]


def find_misnamed_doubles(tests_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(tests_root.rglob("test_*.py"))
        for violation in _find_misnamed_classes(tests_root, module_path)
    ]
