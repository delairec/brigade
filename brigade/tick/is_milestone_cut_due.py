from brigade.tick.build_snapshot import UncutMilestone


def is_milestone_cut_due(uncut: UncutMilestone) -> bool:
    return bool(uncut.open_waves or uncut.todo)
