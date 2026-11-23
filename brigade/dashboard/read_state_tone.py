NEUTRAL_TONE = "faint"
STATE_TONES = {
    "parked": "you",
    "blocked": "you",
    "paused": "you",
    "running": "work",
    "open": "work",
    "fixing": "work",
    "pr_open": "review",
    "verifying": "review",
    "changes_requested": "review",
    "merged": "done",
    "verified": "done",
    "done": "done",
    "closed": "done",
    "reached": "done",
    "ended": "done",
    "blocked:quota": "limit",
    "wall_limit": "limit",
    "turn_limit": "limit",
    "soft_limit": "limit",
    "dead": "failed",
    "failed": "failed",
    "cancelled": "off",
    "stopped": "off",
    "dismissed": "off",
}


def read_state_tone(state: str) -> str:
    return STATE_TONES.get(state, NEUTRAL_TONE)
