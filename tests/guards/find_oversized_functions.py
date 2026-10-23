import ast
from pathlib import Path

LINE_BOUND = 30
PARAMETER_BOUND = 4
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
RECEIVERS = ("self", "cls")


def _count_parameters(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    arguments = function.args
    parameters = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg]
    return len([parameter for parameter in parameters if parameter is not None and parameter.arg not in RECEIVERS])


def _describe_oversize(function: ast.FunctionDef | ast.AsyncFunctionDef, location: str) -> list[str]:
    findings = []
    span = function.end_lineno - function.lineno + 1
    if span > LINE_BOUND:
        findings.append(f"{location}:{function.lineno} {function.name} spans {span} lines, over {LINE_BOUND}")
    parameters = _count_parameters(function)
    if parameters > PARAMETER_BOUND:
        findings.append(
            f"{location}:{function.lineno} {function.name} takes {parameters} parameters, over {PARAMETER_BOUND}"
        )
    return findings


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    functions = [
        node
        for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
        if isinstance(node, FUNCTION_NODES)
    ]
    return [
        finding
        for function in sorted(functions, key=lambda function: function.lineno)
        for finding in _describe_oversize(function, location)
    ]


def find_oversized_functions(package_root: Path) -> list[str]:
    return [
        finding
        for module_path in sorted(package_root.rglob("*.py"))
        for finding in _inspect_module(package_root, module_path)
    ]
