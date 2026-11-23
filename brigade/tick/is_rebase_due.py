from brigade.tick.build_snapshot import MilestoneFacts


def is_rebase_due(milestone: MilestoneFacts) -> bool:
    return milestone.behind_main and not milestone.rebase_run_live and milestone.blocked_rebase is None
