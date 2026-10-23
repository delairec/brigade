import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

ACCEPTED_SUFFIXES = ("Test", "TestCase", "Double", "Arrangement")


def _find_misnamed_classes(module: GuardedModule) -> list[Finding]:
    return [
        (node.lineno, 0, f"{node.name} lacks the Double suffix")
        for node in module.tree.body
        if isinstance(node, ast.ClassDef) and not node.name.endswith(ACCEPTED_SUFFIXES)
    ]


def find_misnamed_doubles(tests_root: Path) -> list[str]:
    return find_violations(tests_root, _find_misnamed_classes, pattern="test_*.py")
