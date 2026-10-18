from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.git.list_commits import list_commits
from brigade.ledger.format_instant import format_instant
from brigade.runtime import Runtime

NAME = "git-log"


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    commits = list_commits(runtime.run_process, inputs.project, inputs.since)
    items = [
        {
            "sha": commit.sha,
            "author": commit.author,
            "date": format_instant(commit.date),
            "subject": commit.subject,
            "files": list(commit.files),
        }
        for commit in commits
    ]
    files = {file for commit in commits for file in commit.files}
    return describe_collection(NAME, runtime, {"commits": len(commits), "files": len(files)}, items)
