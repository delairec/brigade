import ast
from pathlib import Path

RUNTIME_PARAMETER = "runtime"
RUNTIME_TYPE = "Runtime"
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


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


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    functions = [
        node
        for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
        if _takes_unannotated_runtime(node)
    ]
    return [
        f"{location}:{function.lineno} {_describe(function)} takes {RUNTIME_PARAMETER} without"
        f" {RUNTIME_PARAMETER}: {RUNTIME_TYPE}"
        for function in sorted(functions, key=lambda function: function.lineno)
    ]


def find_unannotated_runtimes(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        for violation in _inspect_module(package_root, module_path)
    ]
