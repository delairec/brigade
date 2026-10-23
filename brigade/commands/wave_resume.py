import argparse

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.runtime import Runtime
from brigade.waves.read_wave_pause import read_wave_pause
from brigade.waves.require_wave_summary import require_wave_summary

DOCUMENT_SCHEMA_VERSION = 1
FORGE_ACCOUNT_REASON = "forge_account"
NOTHING_RESUMED = "no wave is paused on the forge account"


def _render_text(document: dict) -> str:
    return "\n".join(f"wave {resumed['wave']} resumed" for resumed in document["resumed"]) or NOTHING_RESUMED


def _list_forge_account_pauses(events: tuple) -> list[tuple[str, str]]:
    waves = dict.fromkeys(event.wave for event in events if isinstance(event, WavePaused))
    return [
        (wave, FORGE_ACCOUNT_REASON)
        for wave in waves
        if getattr(read_wave_pause(events, wave), "reason", None) == FORGE_ACCOUNT_REASON
    ]


def _find_wave_pause(entries: tuple, wave: str) -> list[tuple[str, str]]:
    require_wave_summary(entries, wave)
    pause = read_wave_pause(tuple(entry.event for entry in entries), wave)
    if pause is None:
        raise BrigadeError(f"the wave {wave} is running, not paused")
    return [(wave, pause.reason)]


def wave_resume(request: argparse.Namespace, runtime: Runtime) -> dict:
    entries = read_ledger(runtime.paths.state_root).entries
    if request.wave is None:
        paused = _list_forge_account_pauses(tuple(entry.event for entry in entries))
    else:
        paused = _find_wave_pause(entries, request.wave)
    for wave, reason in paused:
        append_event(runtime.paths, runtime.now, WaveResumed(wave=wave, reason=reason))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "resumed": [{"wave": wave, "reason": reason} for wave, reason in paused],
    }


COMMAND = Command(
    path=("wave", "resume"),
    help="resume the wave named, or every wave paused on the forge account",
    arguments=(Argument(("wave",), {"nargs": "?", "help": "the name of the wave to resume"}),),
    run=wave_resume,
    render_text=_render_text,
)
