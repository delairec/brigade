from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.runtime import Runtime
from brigade.waves.describe_request import describe_request
from brigade.waves.read_wave_pause import read_wave_pause
from brigade.waves.read_wave_request import read_wave_request
from brigade.waves.require_wave_name import require_wave_name

DOCUMENT_SCHEMA_VERSION = 1
FORGE_ACCOUNT_REASON = "forge_account"
NOTHING_RESUMED = "no wave is paused on the forge account"


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return "\n".join(f"wave {resumed['wave']} resumed" for resumed in document["resumed"]) or NOTHING_RESUMED


def _decide_exit_code(document: dict) -> int:
    return 0


def _list_forge_account_pauses(events: tuple) -> list[tuple[str, str]]:
    waves = dict.fromkeys(event.wave for event in events if isinstance(event, WavePaused))
    return [
        (wave, FORGE_ACCOUNT_REASON)
        for wave in waves
        if getattr(read_wave_pause(events, wave), "reason", None) == FORGE_ACCOUNT_REASON
    ]


def _find_request_pause(runtime: Runtime, events: tuple, name: str) -> list[tuple[str, str]]:
    wave = require_wave_name(events, describe_request(read_wave_request(runtime, name)))
    pause = read_wave_pause(events, wave)
    if pause is None:
        raise BrigadeError(f"the wave {wave} of @REQUEST.{name} is running, not paused")
    return [(wave, pause.reason)]


def wave_resume(request, runtime: Runtime) -> dict:
    events = tuple(entry.event for entry in read_ledger(runtime.paths.state_root).entries)
    if request.request is None:
        paused = _list_forge_account_pauses(events)
    else:
        paused = _find_request_pause(runtime, events, request.request)
    for wave, reason in paused:
        append_event(runtime.paths, runtime.now, WaveResumed(wave=wave, reason=reason))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "resumed": [{"wave": wave, "reason": reason} for wave, reason in paused],
    }


COMMAND = Command(
    path=("wave", "resume"),
    help="resume the wave of a request, or every wave paused on the forge account",
    arguments=(Argument(("request",), {"nargs": "?", "help": "the name of the REQUEST whose wave resumes"}),),
    run=wave_resume,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
