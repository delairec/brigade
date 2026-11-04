from collections.abc import Callable

from brigade.system.run_process import ProcessRecord, ProcessRequest


def _key_request(request: ProcessRequest) -> tuple:
    return (
        request.argv,
        request.cwd,
        request.timeout_s,
        request.acceptable_exit_codes,
        request.stdin,
        tuple(sorted(request.environment.items())),
    )


def remember_process_records(
    run_process: Callable[[ProcessRequest], ProcessRecord],
) -> Callable[[ProcessRequest], ProcessRecord]:
    records: dict[tuple, ProcessRecord] = {}

    def run_once(request: ProcessRequest) -> ProcessRecord:
        key = _key_request(request)
        if key not in records:
            records[key] = run_process(request)
        return records[key]

    return run_once
