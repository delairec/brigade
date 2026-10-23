import ast
import io
import tokenize
from pathlib import Path

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


def _inspect_module(tests_root: Path, module_path: Path) -> list[str]:
    location = Path(tests_root.name, module_path.relative_to(tests_root)).as_posix()
    source = module_path.read_text(encoding="utf-8")
    delimiter_lines = _delimiter_lines(source, OPENING_DELIMITERS)
    assert_lines = _delimiter_lines(source, (ASSERT_DELIMITER,))
    methods = [
        statement
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef)
        for statement in node.body
        if isinstance(statement, ast.FunctionDef) and statement.name.startswith("test")
    ]
    preparations = [
        f"{location}:{method.lineno} {method.name} prepares something before its first delimiter"
        for method in methods
        if not _opens_on_a_delimiter(method, delimiter_lines)
    ]
    gestures = [
        f"{location}:{line} {method.name} acts after its last # Assert"
        for method in methods
        for line in _gesture_lines_after_the_last_assert(method, assert_lines)
    ]
    return preparations + gestures


def find_preparations_before_delimiters(tests_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(tests_root.rglob("test_*.py"))
        for violation in _inspect_module(tests_root, module_path)
    ]
