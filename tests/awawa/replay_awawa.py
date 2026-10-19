import hashlib
import json
import re
import sys
from pathlib import Path

from tests.awawa.volatile_value_masker import VolatileValueMasker
from tests.process_launcher import ProcessLauncher

MISSING_RECORDING_EXIT_CODE = 70
IMPL_ANCHOR_PATH = re.compile(r'\bIMPL\s+"([^"]+?)::')


def _list_anchored_files(root: Path, corpus_files: list[Path]) -> list[Path]:
    paths = {root / match for file in corpus_files for match in IMPL_ANCHOR_PATH.findall(_read_input(file) or "")}
    return sorted(path for path in paths if path.is_file())


def _list_input_files(path: Path) -> list[Path]:
    if path.is_dir():
        corpus_files = sorted(path.rglob("*.awawa"))
        return corpus_files + _list_anchored_files(path, corpus_files)
    return [path]


def _read_input(file: Path) -> str | None:
    try:
        return file.read_text()
    except PermissionError:
        return None


def _mask_input(file: Path, masker: VolatileValueMasker) -> str | None:
    content = _read_input(file)
    return None if content is None else masker.mask(content)


def _describe_call(arguments: list[str], cwd: Path, masker: VolatileValueMasker) -> tuple[dict, list[Path]]:
    masked_cwd = masker.mask(str(cwd))
    masked_arguments = [masker.mask(argument) for argument in arguments]
    existing = [cwd / argument for argument in arguments if (cwd / argument).exists()]
    files = [file for path in existing for file in _list_input_files(path)]
    call = {
        "arguments": masked_arguments,
        "cwd": masked_cwd,
        "directories": [masker.mask(str(path)) for path in existing if path.is_dir()],
        "inputs": {masker.mask(str(file)): _mask_input(file, masker) for file in files},
    }
    return call, files


def _find_recording(recordings: Path, call: dict) -> dict | None:
    for path in sorted(recordings.glob("*.json")):
        recording = json.loads(path.read_text())
        if recording["call"] == call:
            return recording
    return None


def _name_recording(call: dict) -> str:
    digest = hashlib.sha256(json.dumps(call, sort_keys=True).encode()).hexdigest()[:12]
    command = next((argument for argument in call["arguments"] if not argument.startswith("-")), "version")
    return f"{command}-{digest}.json"


def _record(configuration: dict, arguments: list[str], call: dict, files: list[Path], masker) -> dict:
    before = {file: _read_input(file) for file in files}
    completed = ProcessLauncher.run(
        [configuration["real_awawa"], *arguments], capture_output=True, text=True, check=False
    )
    recording = {
        "version": configuration["version"],
        "call": call,
        "outcome": {
            "stdout": masker.mask(completed.stdout),
            "stderr": masker.mask(completed.stderr),
            "exit_code": completed.returncode,
            "rewritten": {
                masker.mask(str(file)): _mask_input(file, masker)
                for file in files
                if file.exists() and _read_input(file) != before[file]
            },
        },
    }
    recording["run_order"] = masker.order_run_ids()
    recordings = Path(configuration["recordings"])
    recordings.mkdir(parents=True, exist_ok=True)
    (recordings / _name_recording(call)).write_text(json.dumps(recording, indent=2, sort_keys=True) + "\n")
    return recording


def _report_miss(configuration: dict, arguments: list[str]) -> int:
    line = f"awawa has no recording of: awawa {' '.join(arguments)}\n"
    with Path(configuration["misses"]).open("a") as misses:
        misses.write(line)
    sys.stderr.write(line)
    return MISSING_RECORDING_EXIT_CODE


def main(argv: list[str]) -> int:
    configuration = json.loads(Path(argv[0]).read_text())
    arguments = argv[1:]
    masker = VolatileValueMasker(configuration["temporary_roots"])
    call, files = _describe_call(arguments, Path.cwd(), masker)
    if configuration["real_awawa"] is not None:
        recording = _record(configuration, arguments, call, files, masker)
    else:
        recording = _find_recording(Path(configuration["recordings"]), call)
    if recording is None:
        return _report_miss(configuration, arguments)
    outcome = recording["outcome"]
    for path, content in outcome["rewritten"].items():
        Path(masker.unmask(path)).write_text(masker.unmask(content))
    sys.stdout.write(masker.unmask(outcome["stdout"]))
    sys.stderr.write(masker.unmask(outcome["stderr"]))
    return outcome["exit_code"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
