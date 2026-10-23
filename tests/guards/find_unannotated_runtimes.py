import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

RUNTIME_PARAMETER = "runtime"
RUNTIME_TYPE = "Runtime"
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
NAMED_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
PRIVATE_PREFIX = "_"
RECEIVERS = ("self", "cls")


def _list_parameters(function: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> list[ast.arg]:
    arguments = function.args
    parameters = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
    if arguments.vararg is not None:
        parameters.append(arguments.vararg)
    if arguments.kwarg is not None:
        parameters.append(arguments.kwarg)
    return parameters


def _is_annotated_runtime(parameter: ast.arg) -> bool:
    return isinstance(parameter.annotation, ast.Name) and parameter.annotation.id == RUNTIME_TYPE


def _takes_unannotated_runtime(node: ast.AST) -> bool:
    if not isinstance(node, FUNCTION_NODES):
        return False
    return any(
        parameter.arg == RUNTIME_PARAMETER and not _is_annotated_runtime(parameter)
        for parameter in _list_parameters(node)
    )


def _describe(function: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> str:
    if isinstance(function, ast.Lambda):
        return "a lambda"
    return function.name


def _describe_public_signature(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    if function.name.startswith(PRIVATE_PREFIX):
        return []
    unannotated = [
        f"{function.name} leaves {parameter.arg} unannotated"
        for parameter in _list_parameters(function)
        if parameter.annotation is None and parameter.arg not in (*RECEIVERS, RUNTIME_PARAMETER)
    ]
    if function.returns is None:
        unannotated.append(f"{function.name} leaves its return unannotated")
    return unannotated


def _find_in_module(module: GuardedModule) -> list[Finding]:
    nodes = list(ast.walk(module.tree))
    findings = [
        (
            function.lineno,
            0,
            f"{_describe(function)} takes {RUNTIME_PARAMETER} without {RUNTIME_PARAMETER}: {RUNTIME_TYPE}",
        )
        for function in nodes
        if _takes_unannotated_runtime(function)
    ]
    findings.extend(
        (function.lineno, rank, violation)
        for function in nodes
        if isinstance(function, NAMED_FUNCTION_NODES)
        for rank, violation in enumerate(_describe_public_signature(function), start=1)
    )
    return findings


def find_unannotated_runtimes(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module)
