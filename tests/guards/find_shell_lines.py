import ast
import itertools
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

SHELLS = ("sh", "bash", "dash", "zsh", "ksh")
SHELL_CALLS = ("system", "popen")
SHELL_OPERATORS = ("&&", "||", ">", "<", "$(", "`")
SHELL_COMMAND_OPTION = "-c"
CRONTAB_TEMPLATE_PREFIX = "crontab"
SYSTEMD_COMMAND_PREFIX = "Exec"
TEMPLATE_PATTERN = "*.tpl"


def _find_shell_launch(words: list[str]) -> str | None:
    return next(
        (
            word
            for word, following in itertools.pairwise(words)
            if Path(word).name in SHELLS and following == SHELL_COMMAND_OPTION
        ),
        None,
    )


def _find_operator(words: list[str]) -> str | None:
    if words[:1] == ["["] or (words[:1] == ["test"] and words[1:2] and words[1].startswith("-")):
        return words[0]
    return next((operator for operator in SHELL_OPERATORS for word in words if operator in word), None)


def _argv_words(argv: list[ast.expr]) -> list[str]:
    return [element.value for element in argv if isinstance(element, ast.Constant) and isinstance(element.value, str)]


def _describe_argv(node: ast.Tuple | ast.List) -> str | None:
    words = _argv_words(node.elts)
    shell = _find_shell_launch(words)
    if shell:
        return f"builds an argv opening on the shell {shell}"
    operator = _find_operator(words)
    return f"puts the shell operator {operator} in an argv" if operator else None


def _describe_call(node: ast.Call) -> str | None:
    if any(
        keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
        for keyword in node.keywords
    ):
        return "passes shell=True"
    function = node.func
    if (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "os"
        and function.attr in SHELL_CALLS
    ):
        return f"calls os.{function.attr}"
    return None


def _describe_node(node: ast.AST) -> str | None:
    if isinstance(node, (ast.Tuple, ast.List)):
        return _describe_argv(node)
    if isinstance(node, ast.Call):
        return _describe_call(node)
    return None


def _find_in_module(module: GuardedModule) -> list[Finding]:
    findings = []
    for node in ast.walk(module.tree):
        description = _describe_node(node)
        if description:
            findings.append((node.lineno, node.col_offset, description))
    return findings


def _command_of(template_name: str, line: str) -> str | None:
    if template_name.startswith(CRONTAB_TEMPLATE_PREFIX):
        return line
    if line.startswith(SYSTEMD_COMMAND_PREFIX):
        return line.partition("=")[2]
    return None


def _describe_command(command: str) -> str | None:
    words = command.replace('"', " ").replace("'", " ").split()
    if any(Path(word).name in SHELLS for word in words):
        return "runs a shell in a command line"
    operator = _find_operator(words)
    return f"puts the shell operator {operator} in a command line" if operator else None


def _find_in_template(root: Path, template_path: Path) -> list[str]:
    location = Path(root.name, template_path.relative_to(root)).as_posix()
    violations = []
    for number, line in enumerate(template_path.read_text(encoding="utf-8").splitlines(), start=1):
        command = _command_of(template_path.name, line)
        description = None if command is None else _describe_command(command)
        if description:
            violations.append(f"{location}:{number} {description}")
    return violations


def find_shell_lines(package_root: Path) -> list[str]:
    module_violations = find_violations(package_root, _find_in_module)
    template_violations = [
        violation
        for template_path in sorted(package_root.rglob(TEMPLATE_PATTERN))
        for violation in _find_in_template(package_root, template_path)
    ]
    return module_violations + template_violations
