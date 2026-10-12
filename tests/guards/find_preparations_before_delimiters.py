import ast
import io
import tokenize
from pathlib import Path

OPENING_DELIMITERS = ("# Arrange", "# Act")
BLOCKS_HOLDING_THE_DELIMITERS = (ast.For, ast.With)


def _delimiter_lines(source: str) -> list[int]:
    return [
        token.start[0]
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.string.strip() in OPENING_DELIMITERS
    ]


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
    delimiter_lines = _delimiter_lines(source)
    methods = [
        statement
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef)
        for statement in node.body
        if isinstance(statement, ast.FunctionDef) and statement.name.startswith("test")
    ]
    return [
        f"{location}:{method.lineno} {method.name} prepares something before its first delimiter"
        for method in methods
        if not _opens_on_a_delimiter(method, delimiter_lines)
    ]


def find_preparations_before_delimiters(tests_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(tests_root.rglob("test_*.py"))
        for violation in _inspect_module(tests_root, module_path)
    ]
