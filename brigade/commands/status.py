import argparse

from brigade.command import Command
from brigade.corpus.read_entities import Entity
from brigade.inbox.read_inbox import NEW_STATUS, Signal, read_inbox
from brigade.inbox.render_age import render_age
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.sum_quota_usage import sum_quota_usage
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.studies.describe_study_row import describe_study_row
from brigade.studies.read_last_study_orders import read_last_study_orders
from brigade.studies.read_studies import read_studies
from brigade.studies.record_scan_signals import SCAN_KIND
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.tick.describe_heartbeat import describe_heartbeat
from brigade.tick.describe_study_facts import describe_study_facts
from brigade.tick.is_study_due import is_study_due
from brigade.tick.read_heartbeat import read_heartbeat
from brigade.waves.read_wave_pause import read_wave_pause
from brigade.waves.summarize_waves import summarize_waves

DOCUMENT_SCHEMA_VERSION = 1
PAUSED_STATUS = "paused"
ACTIVE_STATUS = "active"
QUOTA_REASON = "quota"
DUE = "due"
NEVER = "never"
FINGERPRINT_SEPARATOR = ":"


def _is_paused(project: Entity) -> bool:
    return any(field.name == "STATUS" and field.value == PAUSED_STATUS for field in project.fields)


def _list_open_waves(entries: tuple[LedgerEntry, ...]) -> list[dict]:
    events = tuple(entry.event for entry in entries)
    waves = []
    for summary in summarize_waves(entries):
        if not summary.is_open:
            continue
        pause = read_wave_pause(events, summary.started.wave)
        waves.append(
            {
                "wave": summary.started.wave,
                "project": summary.started.project,
                "branch": summary.started.branch,
                "last_event": summary.last_event,
                "tasks": len(summary.started.tasks),
                "pause": None if pause is None else pause.to_document(),
            }
        )
    return waves


def _describe_quota(entries: tuple[LedgerEntry, ...], waves: list[dict], runtime: Runtime) -> dict:
    window_hours = read_configuration(runtime, CONFIGURATION_OPTIONAL).quota_window_hours
    return {
        **sum_quota_usage(entries, runtime.now, window_hours),
        "paused_waves": [
            {"wave": wave["wave"], "resume_at": wave["pause"]["resume_at"]}
            for wave in waves
            if wave["pause"] is not None and wave["pause"]["reason"] == QUOTA_REASON
        ],
    }


def _list_studies_to_watch(runtime: Runtime) -> list[dict]:
    last_orders = read_last_study_orders(read_ledger(runtime.paths.state_root).entries)
    studies = []
    for study in read_studies(runtime):
        last_order = last_orders.get(study.name)
        facts = describe_study_facts(study, last_order)
        due = is_study_due(facts, runtime.now)
        if due or facts.parked:
            studies.append({**describe_study_row(study, last_order), "due": due})
    return studies


def _list_scans(new_signals: list[Signal]) -> list[dict]:
    ages_by_study: dict[str, list[int]] = {}
    for signal in new_signals:
        if signal.kind == SCAN_KIND:
            study = signal.fingerprint.partition(FINGERPRINT_SEPARATOR)[0]
            ages_by_study.setdefault(study, []).append(signal.age_s)
    return [
        {"study": study, "signals": len(ages), "oldest_age_s": max(ages)}
        for study, ages in sorted(ages_by_study.items())
    ]


def _describe_pause(pause: dict) -> str:
    if pause["resume_at"] is None:
        return f"paused on {pause['reason']}"
    return f"paused on {pause['reason']} until {pause['resume_at']}"


def _render_wave(wave: dict) -> str:
    line = f"wave       {wave['wave']} of {wave['project']}, {wave['last_event']}"
    return line if wave["pause"] is None else f"{line}, {_describe_pause(wave['pause'])}"


def _render_quota(quota: dict) -> str:
    usage = ", ".join(f"{measure} {tokens}" for measure, tokens in quota["usage"].items())
    return f"quota      over {quota['window_hours']} hours: {usage}; {quota['runs_without_usage']} runs without usage"


def _render_last_tick(last_tick: dict | None) -> str:
    if last_tick is None:
        return NEVER
    return f"{last_tick['ts']}, {last_tick['actions_applied']} actions applied in {last_tick['duration_ms']} ms"


def _render_scan(scan: dict) -> str:
    return f"scan       {scan['study']}, {scan['signals']} new signals, the oldest {render_age(scan['oldest_age_s'])}"


def _render_study(study: dict) -> str:
    return f"study      {study['name']}, {DUE if study['due'] else study['outcome']}"


def _render_text(document: dict) -> str:
    return "\n".join(
        [
            *(
                f"project    {project['name']}, {PAUSED_STATUS if project['paused'] else ACTIVE_STATUS}"
                for project in document["projects"]
            ),
            *(_render_wave(wave) for wave in document["waves"]),
            f"inbox      {document['inbox']['new_signals']} new signals",
            *(_render_scan(scan) for scan in document["inbox"]["scans"]),
            _render_quota(document["quota"]),
            f"last tick  {_render_last_tick(document['last_tick'])}",
            *(_render_study(study) for study in document["studies"]),
        ]
    )


def status(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    entries = read_ledger(runtime.paths.state_root).entries
    waves = _list_open_waves(entries)
    new_signals = [
        signal for signal in read_inbox(runtime.paths.state_root, runtime.now) if signal.status == NEW_STATUS
    ]
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "projects": [{"name": project.name, "paused": _is_paused(project)} for project in read_projects(runtime)],
        "waves": waves,
        "inbox": {"new_signals": len(new_signals), "scans": _list_scans(new_signals)},
        "quota": _describe_quota(entries, waves, runtime),
        "last_tick": describe_heartbeat(read_heartbeat(runtime.paths.heartbeat_file)),
        "studies": _list_studies_to_watch(runtime),
    }


COMMAND = Command(
    path=("status",),
    help="print the Home document: the projects, the open waves, the inbox and the scans holding new signals, the quota, the last tick and the studies",
    run=status,
    render_text=_render_text,
)
