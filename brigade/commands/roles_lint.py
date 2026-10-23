from brigade.command import Command
from brigade.roles.check_front_matter import check_front_matter
from brigade.roles.list_built_in_role_files import list_built_in_role_files
from brigade.roles.list_machine_role_files import list_machine_role_files
from brigade.roles.parse_role_file import RoleFileUnreadable, parse_role_file
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
BUILT_IN_DIRECTORY = "brigade/roles/data"


def _create_finding(file: str, key, problem: str) -> dict:
    return {"file": file, "key": key, "problem": problem}


def _check_role_file(file: str, text: str, first_declarations: dict) -> list[dict]:
    try:
        front_matter = parse_role_file(text).front_matter
    except RoleFileUnreadable as unreadable:
        return [_create_finding(file, None, str(unreadable))]
    findings = [_create_finding(file, problem.key, problem.problem) for problem in check_front_matter(front_matter)]
    slot = front_matter.get("slot")
    if slot in first_declarations:
        findings.append(_create_finding(file, "slot", f"{slot} is also declared by {first_declarations[slot]}"))
    elif slot is not None:
        first_declarations[slot] = file
    return findings


def _render_finding(finding: dict) -> str:
    if finding["key"] is None:
        return f"{finding['file']}: {finding['problem']}"
    return f"{finding['file']}: {finding['key']} {finding['problem']}"


def _summarise(document: dict) -> str:
    count = len(document["findings"])
    noun = "finding" if count == 1 else "findings"
    return f"roles lint: {len(document['files'])} files, {count} {noun}"


def _render_text(document: dict) -> str:
    if not document["findings"]:
        return _summarise(document)
    return "\n".join([*(_render_finding(finding) for finding in document["findings"]), "", _summarise(document)])


def _decide_exit_code(document: dict) -> int:
    if document["findings"]:
        return 1
    return 0


def roles_lint(request, runtime: Runtime) -> dict:
    built_in_files = [
        (f"{BUILT_IN_DIRECTORY}/{entry.name}", entry.read_text(encoding="utf-8"))
        for entry in list_built_in_role_files()
    ]
    machine_files = [
        (str(path), path.read_text(encoding="utf-8")) for path in list_machine_role_files(runtime.paths.config_root)
    ]
    built_in_findings = [finding for file, text in built_in_files for finding in _check_role_file(file, text, {})]
    machine_declarations = {}
    machine_findings = [
        finding for file, text in machine_files for finding in _check_role_file(file, text, machine_declarations)
    ]
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "files": [file for file, _ in [*built_in_files, *machine_files]],
        "findings": [*built_in_findings, *machine_findings],
    }


COMMAND = Command(
    path=("roles", "lint"),
    help="check the built-in and the machine role files",
    group_help="list, show and lint the roles each slot resolves to",
    run=roles_lint,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
