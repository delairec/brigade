import shlex
from pathlib import Path


def describe_merge_command(repository: Path, branch: str) -> str:
    return shlex.join(("git", "-C", str(repository), "merge", branch))
