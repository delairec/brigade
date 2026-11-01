from html import escape
from urllib.parse import quote

from brigade.dashboard.render_action import render_action
from brigade.inbox.render_age import render_age

NEVER = "never"
DUE = "due"


def _describe_pause(reason: str, resume_at: str | None) -> str:
    if resume_at is None:
        return f"paused on {escape(reason)}"
    return f"paused on {escape(reason)} until {escape(resume_at)}"


def _render_section(heading: str, body: str) -> str:
    return f"<section><h2>{heading}</h2>{body}</section>"


def _render_list(items: list[str]) -> str:
    return f"<ul>{''.join(f'<li>{item}</li>' for item in items)}</ul>"


def _render_project(project: dict) -> str:
    name = project["name"]
    if project["paused"]:
        return f"{escape(name)}, paused{render_action(('projects', name, 'resume'), 'resume')}"
    return f"{escape(name)}, active{render_action(('projects', name, 'pause'), 'pause')}"


def _render_wave(wave: dict) -> str:
    name = wave["wave"]
    line = (
        f'<a href="#waves/{escape(quote(name, safe=""))}">{escape(name)}</a>'
        f" of {escape(wave['project'])}, {escape(wave['last_event'])}"
    )
    pause = wave["pause"]
    if pause is None:
        return line
    resume = render_action(("waves", name, "resume"), "resume")
    return f"{line}, {_describe_pause(pause['reason'], pause['resume_at'])}{resume}"


def _render_quota(quota: dict) -> str:
    usage = "".join(f"<dt>{escape(measure)}</dt><dd>{tokens}</dd>" for measure, tokens in quota["usage"].items())
    paused = [f"{escape(wave['wave'])} {_describe_pause('quota', wave['resume_at'])}" for wave in quota["paused_waves"]]
    return (
        f"<p>over the last {quota['window_hours']} hours, {quota['runs_without_usage']} runs without usage</p>"
        f"<dl>{usage}</dl>{_render_list(paused) if paused else ''}"
    )


def _render_last_tick(last_tick: dict | None) -> str:
    if last_tick is None:
        return f"<p>{NEVER}</p>"
    return (
        f"<p>{escape(last_tick['ts'])}, {last_tick['actions_applied']} actions applied"
        f" in {last_tick['duration_ms']} ms</p>"
    )


def _render_inbox(inbox: dict) -> str:
    scans = [
        f"{escape(scan['study'])}, {scan['signals']} new signals, the oldest {render_age(scan['oldest_age_s'])}"
        for scan in inbox["scans"]
    ]
    return f"<p>{inbox['new_signals']} new signals</p>{_render_list(scans)}"


def _render_study(study: dict) -> str:
    return f"{escape(study['name'])}, {DUE if study['due'] else escape(str(study['outcome']))}"


def render_home(document: dict) -> str:
    return "".join(
        [
            _render_section("Projects", _render_list([_render_project(project) for project in document["projects"]])),
            _render_section("Waves", _render_list([_render_wave(wave) for wave in document["waves"]])),
            _render_section("Inbox", _render_inbox(document["inbox"])),
            _render_section("Quota", _render_quota(document["quota"])),
            _render_section("Last tick", _render_last_tick(document["last_tick"])),
            _render_section("Studies", _render_list([_render_study(study) for study in document["studies"]])),
        ]
    )
