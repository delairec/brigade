BRANCH_COLLECTORS = ("pull-request", "task-worktree")


def read_branch(subject: dict) -> dict:
    collected = subject["collected"]
    return next(collected[name]["summary"] for name in BRANCH_COLLECTORS if name in collected)
