import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

LINE_BOUND = 30
PARAMETER_BOUND = 4
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
RECEIVERS = ("self", "cls")


def _count_parameters(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    arguments = function.args
    parameters = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg]
    return len([parameter for parameter in parameters if parameter is not None and parameter.arg not in RECEIVERS])


def _describe_oversize(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    findings = []
    span = function.end_lineno - function.lineno + 1
    if span > LINE_BOUND:
        findings.append((function.lineno, 0, f"{function.name} spans {span} lines, over {LINE_BOUND}"))
    parameters = _count_parameters(function)
    if parameters > PARAMETER_BOUND:
        findings.append((function.lineno, 1, f"{function.name} takes {parameters} parameters, over {PARAMETER_BOUND}"))
    return findings


def _find_in_module(module: GuardedModule) -> list[Finding]:
    return [
        finding
        for node in ast.walk(module.tree)
        if isinstance(node, FUNCTION_NODES)
        for finding in _describe_oversize(node)
    ]


def find_oversized_functions(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module)
