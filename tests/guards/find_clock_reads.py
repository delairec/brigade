import ast
from pathlib import Path

from tests.guards.find_violations import Finding, GuardedModule, find_violations

PACKAGE_ALLOWED_TO_READ = "system"
MODULE_ALLOWED_TO_READ = "runtime.py"
CLOCK_READS = {("time", "monotonic"): "time.monotonic", ("datetime", "now"): "datetime.now"}


def _imported_clock_reads(tree: ast.AST) -> dict[str, str]:
    return {
        alias.asname or alias.name: CLOCK_READS[(node.module, alias.name)]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
        for alias in node.names
        if (node.module, alias.name) in CLOCK_READS
    }


def _owner_name(owner: ast.expr) -> str | None:
    if isinstance(owner, ast.Name):
        return owner.id
    if isinstance(owner, ast.Attribute):
        return owner.attr
    return None


def _name_clock_read(call: ast.Call, imported: dict[str, str]) -> str | None:
    function = call.func
    if isinstance(function, ast.Name):
        return imported.get(function.id)
    if isinstance(function, ast.Attribute):
        return CLOCK_READS.get((_owner_name(function.value), function.attr))
    return None


def _find_in_module(module: GuardedModule) -> list[Finding]:
    imported = _imported_clock_reads(module.tree)
    findings = []
    for node in ast.walk(module.tree):
        clock_read = _name_clock_read(node, imported) if isinstance(node, ast.Call) else None
        if clock_read:
            findings.append((node.lineno, node.col_offset, f"reads {clock_read}"))
    return findings


def _is_inspected(relative_path: Path) -> bool:
    parts = relative_path.parts
    return not (parts[0] == PACKAGE_ALLOWED_TO_READ or parts == (MODULE_ALLOWED_TO_READ,))


def find_clock_reads(package_root: Path) -> list[str]:
    return find_violations(package_root, _find_in_module, is_inspected=_is_inspected)
