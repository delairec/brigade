import ast
from pathlib import Path

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


def _describe_public_signature(function: ast.FunctionDef | ast.AsyncFunctionDef, location: str) -> list[str]:
    if function.name.startswith(PRIVATE_PREFIX):
        return []
    unannotated = [
        f"{location}:{function.lineno} {function.name} leaves {parameter.arg} unannotated"
        for parameter in _list_parameters(function)
        if parameter.annotation is None and parameter.arg not in (*RECEIVERS, RUNTIME_PARAMETER)
    ]
    if function.returns is None:
        unannotated.append(f"{location}:{function.lineno} {function.name} leaves its return unannotated")
    return unannotated


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    nodes = list(ast.walk(ast.parse(module_path.read_text(encoding="utf-8"))))
    findings = [
        (
            function.lineno,
            (
                f"{location}:{function.lineno} {_describe(function)} takes {RUNTIME_PARAMETER} without"
                f" {RUNTIME_PARAMETER}: {RUNTIME_TYPE}"
            ),
        )
        for function in nodes
        if _takes_unannotated_runtime(function)
    ]
    findings.extend(
        (function.lineno, violation)
        for function in nodes
        if isinstance(function, NAMED_FUNCTION_NODES)
        for violation in _describe_public_signature(function, location)
    )
    return [violation for _, violation in sorted(findings, key=lambda finding: finding[0])]


def find_unannotated_runtimes(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        for violation in _inspect_module(package_root, module_path)
    ]
