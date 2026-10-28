from html import escape

from brigade.dashboard.render_action import render_action

ABSENT = "-"
QUEUED_STATE = "queued"
PARKED_STATE = "parked"


def _show(value) -> str:
    return ABSENT if value is None else escape(str(value))


def _render_task(task: dict, wave: str, ledger: dict) -> str:
    name = task["task"]
    line = (
        f"{escape(name)}, pull request {_show(task['pull_request'])}, run {_show(task['run'])},"
        f" {ledger['rounds_by_task'].get(name, 0)} rounds, {_show(ledger['steps_by_task'].get(name))} steps"
    )
    if task["reason"] is not None:
        line = f"{line}, {escape(task['reason'])}"
    if task["state"] == PARKED_STATE:
        line = f"{line}{render_action(('waves', wave, 'tasks', name, 'requeue'), 'requeue')}"
    return f"<li>{line}</li>"


def _render_groups(shown: dict, ledger: dict) -> str:
    groups = {}
    for task in shown["tasks"]:
        groups.setdefault(task["state"] or QUEUED_STATE, []).append(_render_task(task, shown["wave"], ledger))
    return "".join(f"<h3>{escape(state)}</h3><ul>{''.join(items)}</ul>" for state, items in groups.items())


def _render_entry(entry: dict) -> str:
    task = entry["fields"].get("task")
    subject = "" if task is None else f" {escape(task)}"
    return f"<li>{escape(entry['at'])} {escape(entry['event'])}{subject}</li>"


def render_wave(shown: dict, ledger: dict) -> str:
    return (
        f"<section><h2>Wave {escape(shown['wave'])} of {escape(shown['project'])}</h2>"
        f"{_render_groups(shown, ledger)}</section>"
        f"<section><h2>Timeline</h2><ol>{''.join(_render_entry(entry) for entry in ledger['timeline'])}</ol></section>"
    )
