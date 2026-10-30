import re
from importlib.resources import files
from pathlib import Path
from string import Template

from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file
from brigade.tick.actions import LaunchCheckRepair
from brigade.tick.build_snapshot import PreflightFailure
from brigade.tick.name_task_branch import name_task_branch

BRIEF_TEMPLATE = files("brigade.tick") / "data" / "repair-brief.md.tpl"
BRIEFS_DIRECTORY = "briefs"
NO_LOG_KEPT = "The forge keeps no log of this check."
UNREADABLE_LOG = "The log of this check could not be read."
FINDINGS_HEADING = "The other findings of the preflight of the same head:"
COVERAGE_CHECK_WORD = "coverage"
COVERAGE_REMEDY = (
    "The coverage check failed: remove each uncovered line, then write it again from a test that demands it,"
    " seen failing first; never write a test after the code it covers."
)
TERMINAL_ESCAPE_SEQUENCE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\].*?(?:\x07|\x1b\\)|[ -/]+[0-~]|[@-_])")


def _strip_escape_sequences(tail: str) -> str:
    return TERMINAL_ESCAPE_SEQUENCE.sub("", tail)


def _describe_log(log: dict) -> str:
    if log.get("unreadable"):
        return UNREADABLE_LOG
    if log["tail"] is None:
        return NO_LOG_KEPT
    return f"```\n{_strip_escape_sequences(log['tail'])}\n```"


def _describe_findings(failures: tuple[PreflightFailure, ...]) -> str:
    if not failures:
        return ""
    return f"\n{FINDINGS_HEADING}\n" + "".join(
        f"\n## {failure.name}\n\n" + "".join(f"- {finding}\n" for finding in failure.findings) for failure in failures
    )


def _name_remedy(checks: tuple[str, ...]) -> str:
    if not any(COVERAGE_CHECK_WORD in check.casefold() for check in checks):
        return ""
    return f"\n{COVERAGE_REMEDY}\n"


def write_repair_brief(state_root: Path, action: LaunchCheckRepair, logs: list[dict]) -> Path:
    path = state_root / BRIEFS_DIRECTORY / f"{action.wave}-{action.task}-checks.md"
    brief = Template(BRIEF_TEMPLATE.read_text(encoding="utf-8")).substitute(
        pr=action.pr,
        task=action.task,
        project=action.project,
        wave=action.wave,
        branch=action.branch,
        worktree=action.worktree,
        task_branch=name_task_branch(action.branch, action.task),
        logs="".join(f"\n## {log['name']}\n\n{_describe_log(log)}\n" for log in logs),
        findings=_describe_findings(action.findings),
        remedy=_name_remedy(action.checks),
    )
    create_directory(path.parent)
    write_text_file(path, brief)
    return path
