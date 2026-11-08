import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from brigade.corpus.run_awawa import run_awawa
from brigade.git.count_changed_lines import ChangedFile
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.verify.judge_findings import judge_findings

NAME = "untouched_files"
CORPUS_SUFFIX = ".awawa"


@dataclass(frozen=True)
class UntouchedFilesFacts:
    base_tree: Path
    head_tree: Path
    changed: tuple[ChangedFile, ...]
    folder: Path = Path()


def _locate(file: str, tree: Path, folder: Path) -> str:
    return (PurePosixPath(folder) / (tree / file).resolve().relative_to(tree.resolve()).as_posix()).as_posix()


def check_untouched_files(run_process: Callable[[ProcessRequest], ProcessRecord], facts: UntouchedFilesFacts) -> dict:
    record = run_awawa(run_process, facts.head_tree, ("diff", str(facts.base_tree), str(facts.head_tree), "--json"))
    moved = json.loads(record.stdout)
    touched = {
        *(_locate(entity["file"], facts.head_tree, facts.folder) for entity in (*moved["added"], *moved["changed"])),
        *(_locate(entity["file"], facts.base_tree, facts.folder) for entity in moved["removed"]),
    }
    return judge_findings(
        NAME,
        [
            f"{changed.path} changes while none of its entities does"
            for changed in facts.changed
            if changed.path.endswith(CORPUS_SUFFIX)
            and PurePosixPath(changed.path).is_relative_to(PurePosixPath(facts.folder))
            and changed.path not in touched
        ],
    )
