from brigade.tick.head_proof import RED
from brigade.tick.prepare_task_worktree import HoldingHead


def describe_holding_head(held_by: HoldingHead) -> str:
    proof = held_by.proof
    if proof.state == RED:
        commands = ", ".join(f"`{command}`" for command in proof.failed_commands)
        return f"{held_by.branch} is red at {proof.commit}, {commands} failed"
    return f"{held_by.branch} is {proof.state} at {proof.commit}"
