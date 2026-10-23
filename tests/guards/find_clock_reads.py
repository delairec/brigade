import ast
from pathlib import Path

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


def _inspect_module(package_root: Path, module_path: Path) -> list[str]:
    location = Path(package_root.name, module_path.relative_to(package_root)).as_posix()
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported = _imported_clock_reads(tree)
    findings = []
    for node in ast.walk(tree):
        clock_read = _name_clock_read(node, imported) if isinstance(node, ast.Call) else None
        if clock_read:
            findings.append((node.lineno, node.col_offset, f"{location}:{node.lineno} reads {clock_read}"))
    return [violation for _, _, violation in sorted(findings)]


def _may_read_the_clock(package_root: Path, module_path: Path) -> bool:
    parts = module_path.relative_to(package_root).parts
    return parts[0] == PACKAGE_ALLOWED_TO_READ or parts == (MODULE_ALLOWED_TO_READ,)


def find_clock_reads(package_root: Path) -> list[str]:
    return [
        violation
        for module_path in sorted(package_root.rglob("*.py"))
        if not _may_read_the_clock(package_root, module_path)
        for violation in _inspect_module(package_root, module_path)
    ]
