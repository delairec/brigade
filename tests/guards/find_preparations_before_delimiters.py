import ast
import io
import tokenize
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

OPENING_DELIMITERS = ("# Arrange", "# Act")
ASSERT_DELIMITER = "# Assert"
BLOCKS_HOLDING_THE_DELIMITERS = (ast.For, ast.With)
GESTURES = ("run_brigade", "communicate")
WAIT_PREFIX = "wait_for"


def _delimiter_lines(source: str, delimiters: tuple[str, ...]) -> list[int]:
    return [
        token.start[0]
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.string.strip() in delimiters
    ]


def _names_a_gesture(call: ast.Call) -> bool:
    callee = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
    return callee in GESTURES or callee.startswith(WAIT_PREFIX)


def _gesture_lines_after_the_last_assert(method: ast.FunctionDef, assert_lines: list[int]) -> list[int]:
    last_assert = max((line for line in assert_lines if method.lineno < line <= method.end_lineno), default=None)
    if last_assert is None:
        return []
    return sorted(
        {
            node.lineno
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and node.lineno > last_assert and _names_a_gesture(node)
        }
    )


def _opens_on_a_delimiter(block: ast.AST, delimiter_lines: list[int]) -> bool:
    first_statement = block.body[0]
    if any(block.lineno < line < first_statement.lineno for line in delimiter_lines):
        return True
    return isinstance(first_statement, BLOCKS_HOLDING_THE_DELIMITERS) and _opens_on_a_delimiter(
        first_statement, delimiter_lines
    )


def _find_in_module(module: GuardedModule) -> list[Finding]:
    delimiter_lines = _delimiter_lines(module.source, OPENING_DELIMITERS)
    assert_lines = _delimiter_lines(module.source, (ASSERT_DELIMITER,))
    methods = [
        statement
        for node in ast.walk(module.tree)
        if isinstance(node, ast.ClassDef)
        for statement in node.body
        if isinstance(statement, ast.FunctionDef) and statement.name.startswith("test")
    ]
    preparations = [
        (method.lineno, 0, f"{method.name} prepares something before its first delimiter")
        for method in methods
        if not _opens_on_a_delimiter(method, delimiter_lines)
    ]
    gestures = [
        (line, 0, f"{method.name} acts after its last # Assert")
        for method in methods
        for line in _gesture_lines_after_the_last_assert(method, assert_lines)
    ]
    return preparations + gestures


def find_preparations_before_delimiters(tests_root: Path) -> list[str]:
    return find_violations(tests_root, _find_in_module, pattern="test_*.py")
