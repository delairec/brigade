from html import escape
from urllib.parse import quote

from brigade.dashboard.render_details import render_details
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.render_age import render_age
from brigade.triage.ratify_pattern import CONSTRAINT_ACTION, CONSTRAINT_KINDS, DISMISS_ACTION

NO_PROJECT = "-"
NO_SIGNAL_AGE = "-"
NEW_STATUS = "new"
RATIFY_ADDRESS = "/api/inbox/ratify/"
DISMISS_ADDRESS = "/api/inbox/dismiss/"
WHAT_RATIFYING_STARTS = {
    "wave": "a request on {target}, planned into a wave",
    "constraint": "a constraint on {target} of the kind chosen, and a request delivering it",
    "order": "an order of its recipe on {target}",
    "dismiss": "nothing: the pattern proposes its own dismissal",
    None: "nothing until the pattern names an action",
}
NOTHING_WITHOUT_TARGET = "nothing until the pattern names a target"
STALE_MARK = ' <span class="stale">stale: its task merged since</span>'
NO_STALE_MARK = ""
NO_REPEATED_PATTERN = ""
NO_PATTERN = render_empty_state("no pattern waits for a decision", "the daily triage proposes one from the new signals")
NO_SIGNAL = render_empty_state(
    "no new signal is in the inbox", "a review thread, a stall, a check run, a note or a scan records one"
)
NO_ANSWER = render_empty_state("no study answer is to read", "a study run writes one")


def _render_button(address: str, label: str) -> str:
    return f'<button data-post="{escape(address)}">{escape(label)}</button>'


def _render_section(heading: str, body: str) -> str:
    return f"<section><h2>{heading}</h2>{body}</section>"


def _render_tiles(document: dict) -> str:
    patterns = document["patterns"]
    signals = document["signals"]
    covered = {signal for pattern in patterns for signal in pattern["signals"]}
    oldest = max((signal["age_s"] for signal in signals), default=None)
    tiles = (
        StatTile(
            label="patterns to decide",
            value=str(len(patterns)),
            perimeter=f"{sum(pattern['repeats'] is not None for pattern in patterns)} of them repeats",
        ),
        StatTile(
            label="new signals",
            value=str(len(signals)),
            perimeter=f"{sum(signal['id'] in covered for signal in signals)} covered by a pattern",
        ),
        StatTile(
            label="oldest signal",
            value=NO_SIGNAL_AGE if oldest is None else render_age(oldest),
            perimeter="the age of the oldest new signal",
        ),
        StatTile(label="study answers", value=str(len(document["answers"])), perimeter="to read"),
    )
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _render_ratification(pattern: dict) -> str:
    address = RATIFY_ADDRESS + quote(pattern["name"], safe="")
    if pattern["action"] != CONSTRAINT_ACTION:
        return _render_button(address, "ratify")
    return "".join(_render_button(f"{address}?kind={kind}", f"ratify as {kind}") for kind in CONSTRAINT_KINDS)


def _render_repeated(pattern: dict, proposed: set[str]) -> str:
    if pattern["repeats"] is None or pattern["repeats"] in proposed:
        return NO_REPEATED_PATTERN
    return f" repeats <code>{escape(pattern['repeats'])}</code>"


def _describe_what_ratifying_starts(pattern: dict) -> str:
    action = pattern["action"]
    if action not in (None, DISMISS_ACTION) and pattern["target"] is None:
        return NOTHING_WITHOUT_TARGET
    return WHAT_RATIFYING_STARTS[action].format(target=pattern["target"])


def _render_pattern(pattern: dict, repeats_of: dict[str, list[dict]], new_signals: set[str]) -> str:
    proposed = set(repeats_of)
    name = pattern["name"]
    starts = _describe_what_ratifying_starts(pattern)
    still_new = sum(signal in new_signals for signal in pattern["signals"])
    repeats = repeats_of[name]
    folded = "".join(_render_pattern(repeat, repeats_of, new_signals) for repeat in repeats)
    return (
        f'<article class="pattern"><h3>{escape(pattern["title"])}</h3>'
        f'<p class="pattern-name"><a href="#inbox/{escape(quote(name, safe=""))}"><code>{escape(name)}</code></a>'
        f"{_render_repeated(pattern, proposed)}</p>"
        f"<p>If ratified: {escape(starts)}</p>"
        f"<p>{still_new} of the {len(pattern['signals'])} signals it cites still new</p>"
        f"{_render_ratification(pattern)}"
        f"{_render_button(DISMISS_ADDRESS + quote(name, safe=''), 'dismiss')}"
        f"{render_details(f'{len(repeats)} repeats', folded) if repeats else ''}</article>"
    )


def _render_patterns(document: dict) -> str:
    patterns = document["patterns"]
    repeats_of = {pattern["name"]: [] for pattern in patterns}
    for pattern in patterns:
        if pattern["repeats"] in repeats_of:
            repeats_of[pattern["repeats"]].append(pattern)
    new_signals = {signal["id"] for signal in document["signals"] if signal["status"] == NEW_STATUS}
    standing = [pattern for pattern in patterns if pattern["repeats"] not in repeats_of]
    return "".join(_render_pattern(pattern, repeats_of, new_signals) for pattern in standing) or NO_PATTERN


def _render_signal(signal: dict) -> str:
    identifier = signal["id"]
    return (
        f'<li><a href="#inbox/{escape(quote(identifier, safe=""))}"><code>{escape(identifier[:SHOWN_ID_LENGTH])}</code></a>'
        f" {escape(signal['project'] or NO_PROJECT)}, {signal['count']} in {escape(render_age(signal['age_s']))}"
        f"{STALE_MARK if signal['stale'] else NO_STALE_MARK}"
        f" {_render_button(DISMISS_ADDRESS + quote(identifier, safe=''), 'dismiss')}</li>"
    )


def _render_signals(document: dict) -> str:
    groups: dict[str, list[dict]] = {}
    for signal in document["signals"]:
        groups.setdefault(signal["kind"], []).append(signal)
    rendered = "".join(
        f"<section><h3>{escape(kind)}</h3><ul>{''.join(_render_signal(signal) for signal in signals)}</ul></section>"
        for kind, signals in groups.items()
    )
    return rendered or NO_SIGNAL


def _render_answer(answer: dict) -> str:
    address = f"#inbox/{quote(answer['id'], safe='')}"
    return (
        f'<li><a href="{escape(address)}">{escape(answer["id"])}</a>'
        f" {escape(answer['study'] or NO_PROJECT)} {escape(answer['project'] or NO_PROJECT)}</li>"
    )


def _render_answers(document: dict) -> str:
    answers = "".join(_render_answer(answer) for answer in document["answers"])
    return f"<ul>{answers}</ul>" if answers else NO_ANSWER


def render_inbox_view(document: dict) -> str:
    sentence = (
        f"{len(document['patterns'])} proposed patterns to decide first,"
        f" then {len(document['signals'])} new signals and {len(document['answers'])} study answers to read."
    )
    return (
        f"{render_status_sentence(sentence)}{_render_tiles(document)}"
        f"{_render_section('Decide first', _render_patterns(document))}"
        f"{_render_section('New signals', _render_signals(document))}"
        f"{_render_section('Study answers', _render_answers(document))}"
    )
