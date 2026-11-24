from html import escape
from urllib.parse import quote, urlencode

from brigade.dashboard.format_clock import format_clock
from brigade.dashboard.read_signal_origin import read_signal_origin
from brigade.dashboard.render_block import Block, render_block
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_field import render_field
from brigade.dashboard.render_fold import Fold, render_fold
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.render_age import render_age
from brigade.triage.ratify_pattern import CONSTRAINT_ACTION, CONSTRAINT_KINDS, DISMISS_ACTION, ORDER_ACTION

NO_PROJECT = "-"
NO_LEDE = ""
DECIDE_FIRST_LEDE = "The patterns that still hold new signals, the most covered first."
NO_ACTION = "-"
NO_SIGNAL_AGE = "-"
RATIFY_ADDRESS = "/api/inbox/ratify/"
DISMISS_ADDRESS = "/api/inbox/dismiss/"
DISMISS_ALL_ADDRESS = "/api/inbox/dismiss-all/"
KIND_PARAMETER = "kind"
KIND_PREFIX = "kind-"
KIND_UNTIL_CHOSEN = CONSTRAINT_KINDS[0]
INBOX_VIEW = "inbox?"
CHOSEN = " selected"
TIMES_SIGN = "\N{MULTIPLICATION SIGN}"
NOT_CHOSEN = ""
HEAD = PageHead(
    title="Inbox",
    lede="What brigade noticed and could not settle alone. You decide: turn a finding into work, or dismiss it.",
)
EXPLAINER = (
    "<p>A <b>signal</b> is one fact brigade saw: a branch left behind, a task that stalled, a failing check, a note"
    " you wrote. The same fact seen again raises the count of its signal.</p>"
    "<p>A <b>pattern</b> is a proposal of the triage: several signals, one cause, one action. <b>Ratify</b> it and"
    " brigade acts: a <b>wave</b> pattern records a request and launches its planner, a <b>constraint</b> pattern"
    " proposes a rule, guard, lint, schema, skill or script, an <b>order</b> pattern runs a recipe."
    " <b>Dismiss</b> it and its signals are dismissed with it.</p>"
    "<p>Start with the patterns: one decision clears many signals.</p>"
)
WHAT_RATIFYING_STARTS = {
    "wave": "a request on {target}, planned into a wave",
    "constraint": "a constraint on {target} of the kind chosen, and a request delivering it",
    "order": "an order of the recipe {recipe} on {target}",
    "dismiss": "nothing: the pattern proposes its own dismissal",
    None: "nothing until the pattern names an action",
}
NOTHING_WITHOUT_TARGET = "nothing until the pattern names a target"
NOTHING_WITHOUT_RECIPE = "nothing until the pattern names a recipe"
STALE_MARK = ' <span class="stale">stale: its task merged since</span>'
NO_STALE_MARK = ""
NO_REPEATED_PATTERN = ""
NO_REPEATS = ""
NO_OTHER_PROPOSAL = ""
PROPOSED_ONCE = ""
SINGLE_CITED_SIGNAL = " · cites 1 signal, new"
OTHER_PROPOSALS_HEADER = (
    '<thead><tr><th>Finding</th><th class="num">Proposed</th><th>Action</th><th class="num">Signals cited</th>'
    "<th></th></tr></thead>"
)
SIGNALS_HEADER = (
    '<thead><tr><th>Signal</th><th>What</th><th class="num">Seen</th><th class="num">First seen</th><th></th>'
    "</tr></thead>"
)
NO_PATTERN = render_empty_state("no pattern waits for a decision", "the daily triage proposes one from the new signals")
NO_SIGNAL = render_empty_state(
    "no new signal is in the inbox", "a review thread, a stall, a check run, a note or a scan records one"
)
NO_ANSWER = render_empty_state("no study answer is to read", "a study run writes one")


def _render_button(address: str, label: str, css_class: str) -> str:
    return f'<button class="{css_class}" type="button" data-post="{escape(address)}">{escape(label)}</button>'


def _render_section(heading: str, lede: str, body: str) -> str:
    return render_block(Block(title=heading, lede=lede, body=body))


def _render_table(header: str, rows: str) -> str:
    return f'<div class="panel scroll"><table>{header}<tbody>{rows}</tbody></table></div>'


def _count_times(count: int) -> str:
    return "once" if count == 1 else f"{count} times"


def _render_explainer() -> str:
    return f'<details class="explainer"><summary>How to read this page</summary><div>{EXPLAINER}</div></details>'


def _count_noun(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _describe_findings(patterns: list[dict]) -> str:
    repeats = sum(len(repeated) for repeated in _read_repeats(patterns).values())
    return f"{_count_noun(len(patterns) - repeats, 'finding')}, {_count_noun(repeats, 'repeat')}"


def _render_tiles(document: dict) -> str:
    patterns = document["patterns"]
    signals = document["signals"]
    covered = {signal for pattern in patterns for signal in pattern["signals"]}
    oldest = max((signal["age_s"] for signal in signals), default=None)
    tiles = (
        StatTile(
            label="patterns to decide",
            value=str(len(patterns)),
            perimeter=_describe_findings(patterns),
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


def _render_kind(name: str, kind: str, kinds: dict[str, str]) -> str:
    chosen_kinds = {**kinds, name: kind}
    leads_to = INBOX_VIEW + urlencode({KIND_PREFIX + pattern: chosen for pattern, chosen in chosen_kinds.items()})
    chosen = CHOSEN if kinds.get(name, KIND_UNTIL_CHOSEN) == kind else NOT_CHOSEN
    return f'<option value="{kind}" data-href="{escape(leads_to)}"{chosen}>{kind}</option>'


def _render_ratification(pattern: dict, kinds: dict[str, str]) -> str:
    name = pattern["name"]
    address = RATIFY_ADDRESS + quote(name, safe="")
    if pattern["action"] != CONSTRAINT_ACTION:
        return _render_button(address, "Ratify", "btn btn-primary")
    selector = KIND_PREFIX + name
    options = "".join(_render_kind(name, kind, kinds) for kind in CONSTRAINT_KINDS)
    chosen = urlencode({KIND_PARAMETER: kinds.get(name, KIND_UNTIL_CHOSEN)})
    control = f'<select id="{escape(selector)}" name="{KIND_PARAMETER}">{options}</select>'
    return render_field("as", selector, control) + _render_button(f"{address}?{chosen}", "Ratify", "btn btn-primary")


def _render_repeated(pattern: dict, proposed: set[str]) -> str:
    if pattern["repeats"] is None or pattern["repeats"] in proposed:
        return NO_REPEATED_PATTERN
    return f" repeats <code>{escape(pattern['repeats'])}</code>"


def _describe_what_ratifying_starts(pattern: dict) -> str:
    action = pattern["action"]
    if action not in (None, DISMISS_ACTION) and pattern["target"] is None:
        return NOTHING_WITHOUT_TARGET
    if action == ORDER_ACTION and pattern["recipe"] is None:
        return NOTHING_WITHOUT_RECIPE
    return WHAT_RATIFYING_STARTS[action].format(target=pattern["target"], recipe=pattern["recipe"])


def _render_repeat(repeat: dict) -> str:
    name = repeat["name"]
    quoted = quote(name, safe="")
    ratify = _render_button(RATIFY_ADDRESS + quoted, "Ratify", "btn")
    dismiss = _render_button(DISMISS_ADDRESS + quoted, "Dismiss", "btn")
    return (
        f'<li><a href="#inbox/{escape(quoted)}"><code>{escape(name)}</code></a> {escape(repeat["title"])}'
        f'<span class="act">{ratify}{dismiss}</span></li>'
    )


def _render_repeats(repeats: list[dict]) -> str:
    if not repeats:
        return NO_REPEATS
    listed = "".join(_render_repeat(repeat) for repeat in repeats)
    return render_fold(
        Fold(summary=_count_noun(len(repeats), "repeat"), detail="", body=f'<ul class="repeats">{listed}</ul>')
    )


def _count_still_new(pattern: dict, new_signals: set[str]) -> int:
    return sum(signal in new_signals for signal in pattern["signals"])


def _describe_proposals(proposals: int) -> str:
    if proposals == 1:
        return PROPOSED_ONCE
    return f" · proposed {proposals} times, {proposals - 1} of them while the first was still undecided"


def _describe_cited(pattern: dict, new_signals: set[str]) -> str:
    cited = len(pattern["signals"])
    if cited == 1:
        return SINGLE_CITED_SIGNAL
    return f" · cites {cited} signals, {_count_still_new(pattern, new_signals)} of them new"


def _render_dismissal(name: str, proposals: int) -> str:
    if proposals == 1:
        return _render_button(DISMISS_ADDRESS + quote(name, safe=""), "Dismiss", "btn")
    return _render_button(DISMISS_ALL_ADDRESS + quote(name, safe=""), f"Dismiss all {proposals}", "btn")


def _render_pattern(pattern: dict, repeats_of: dict[str, list[dict]], new_signals: set[str], kinds: dict) -> str:
    name = pattern["name"]
    proposals = 1 + len(repeats_of[name])
    dismiss = _render_dismissal(name, proposals)
    return (
        f'<li class="needs-you tone-you"><span class="mark">{proposals}{TIMES_SIGN}</span>'
        f"<div><h3>{escape(pattern['title'])}</h3>"
        f'<p class="pattern-name"><a href="#inbox/{escape(quote(name, safe=""))}"><code>{escape(name)}</code></a>'
        f"{_render_repeated(pattern, set(repeats_of))}{_describe_proposals(proposals)}"
        f"{_describe_cited(pattern, new_signals)}</p>"
        f"<p>If ratified: {escape(_describe_what_ratifying_starts(pattern))}</p>"
        f"{_render_repeats(repeats_of[name])}</div>"
        f'<div class="act">{_render_ratification(pattern, kinds)}{dismiss}</div></li>'
    )


def _render_other_proposal(pattern: dict, repeats_of: dict[str, list[dict]]) -> str:
    name = pattern["name"]
    return (
        f'<tr><td>{escape(pattern["title"])}<br><span class="mono muted">{escape(name)}</span></td>'
        f'<td class="num">{_count_times(1 + len(repeats_of[name]))}</td>'
        f"<td>{escape(pattern['action'] or NO_ACTION)}</td>"
        f'<td class="num">{len(pattern["signals"])}</td>'
        f'<td class="num"><a class="btn" href="#inbox/{escape(quote(name, safe=""))}">Open</a></td></tr>'
    )


def _read_repeats(patterns: list[dict]) -> dict[str, list[dict]]:
    repeats_of = {pattern["name"]: [] for pattern in patterns}
    for pattern in patterns:
        if pattern["repeats"] in repeats_of:
            repeats_of[pattern["repeats"]].append(pattern)
    return repeats_of


def _describe_other_proposals(count: int) -> str:
    patterns = "1 pattern" if count == 1 else f"{count} patterns"
    return f"{patterns} whose signals are all dismissed, or that cite none."


def _render_patterns(document: dict, kinds: dict[str, str]) -> str:
    patterns = document["patterns"]
    repeats_of = _read_repeats(patterns)
    new_signals = {signal["id"] for signal in document["signals"]}
    standing = [pattern for pattern in patterns if pattern["repeats"] not in repeats_of]
    holding = sorted(
        (pattern for pattern in standing if _count_still_new(pattern, new_signals)),
        key=lambda pattern: _count_still_new(pattern, new_signals),
        reverse=True,
    )
    to_decide = "".join(_render_pattern(pattern, repeats_of, new_signals, kinds) for pattern in holding)
    others = [pattern for pattern in standing if not _count_still_new(pattern, new_signals)]
    decided_first = _render_section(
        "Decide first", DECIDE_FIRST_LEDE, f'<ul class="panel todo">{to_decide}</ul>' if to_decide else NO_PATTERN
    )
    if not others:
        return decided_first + NO_OTHER_PROPOSAL
    rows = "".join(_render_other_proposal(pattern, repeats_of) for pattern in others)
    lede = _describe_other_proposals(len(others))
    return decided_first + _render_section("Other proposals", lede, _render_table(OTHER_PROPOSALS_HEADER, rows))


def _describe_subject(signal: dict) -> str:
    origin = read_signal_origin(signal)
    if origin.wave is None:
        return escape(origin.subject)
    wave = f'<a class="mono" href="#waves/{escape(quote(origin.wave, safe=""))}">{escape(origin.wave)}</a>'
    return f"{escape(origin.subject)} of {wave} · last action {format_clock(origin.last_action)}"


def _render_signal(signal: dict) -> str:
    identifier = signal["id"]
    address = f"#inbox/{quote(identifier, safe='')}"
    dismiss = _render_button(DISMISS_ADDRESS + quote(identifier, safe=""), "Dismiss", "btn")
    return (
        f'<tr><td class="mono"><a href="{escape(address)}">{escape(identifier[:SHOWN_ID_LENGTH])}</a></td>'
        f"<td>{_describe_subject(signal)}{STALE_MARK if signal['stale'] else NO_STALE_MARK}</td>"
        f'<td class="num">{_count_times(signal["count"])}</td>'
        f'<td class="num">{escape(render_age(signal["age_s"]))} ago</td><td class="num">{dismiss}</td></tr>'
    )


def _count_signals(count: int) -> str:
    return "1 signal" if count == 1 else f"{count} signals"


def _describe_coverage(covered: int, count: int) -> str:
    if not covered:
        return "not covered by any pattern"
    if covered == count:
        return "all covered by a pattern"
    return f"{covered} of {count} covered by a pattern"


def _render_group_of_signals(group: str, signals: list[dict], covered: set[str]) -> str:
    held = sum(signal["id"] in covered for signal in signals)
    oldest = render_age(max(signal["age_s"] for signal in signals))
    detail = f"{_count_signals(len(signals))} · oldest {oldest} · {_describe_coverage(held, len(signals))}"
    rows = "".join(_render_signal(signal) for signal in signals)
    fold = Fold(summary=group, detail=detail, body=_render_table(SIGNALS_HEADER, rows), opened=held < len(signals))
    return render_fold(fold)


def _render_signals(document: dict) -> str:
    covered = {signal for pattern in document["patterns"] for signal in pattern["signals"]}
    groups: dict[str, list[dict]] = {}
    for signal in document["signals"]:
        groups.setdefault(read_signal_origin(signal).group, []).append(signal)
    uncovered_first = sorted(groups.items(), key=lambda group: all(signal["id"] in covered for signal in group[1]))
    rendered = "".join(_render_group_of_signals(group, signals, covered) for group, signals in uncovered_first)
    return rendered or NO_SIGNAL


def _describe_signals(signals: list[dict]) -> str:
    return f"{_count_signals(len(signals))}, by what recorded them." if signals else NO_LEDE


def _render_answer(answer: dict) -> str:
    address = f"#inbox/{quote(answer['id'], safe='')}"
    return (
        f'<li><a href="{escape(address)}">{escape(answer["id"])}</a>'
        f" {escape(answer['study'] or NO_PROJECT)} {escape(answer['project'] or NO_PROJECT)}</li>"
    )


def _render_answers(document: dict) -> str:
    answers = "".join(_render_answer(answer) for answer in document["answers"])
    return f"<ul>{answers}</ul>" if answers else NO_ANSWER


def render_inbox_view(document: dict, kinds: dict[str, str]) -> str:
    sentence = (
        f"{len(document['patterns'])} proposed patterns to decide first,"
        f" then {len(document['signals'])} new signals and {len(document['answers'])} study answers to read."
    )
    return (
        f"{render_page_head(HEAD)}{render_status_sentence(sentence)}{_render_tiles(document)}{_render_explainer()}"
        f"{_render_patterns(document, kinds)}"
        f"{_render_section('New signals', _describe_signals(document['signals']), _render_signals(document))}"
        f"{_render_section('Study answers', NO_LEDE, _render_answers(document))}"
    )
