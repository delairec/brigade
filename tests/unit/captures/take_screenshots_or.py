from brigade.system.run_process import ProcessRecord
from tests.unit.captures.take_screenshot import take_screenshot


def take_screenshots_or(run_process):
    def run(request) -> ProcessRecord:
        if request.argv[0] == "firefox":
            exit_code, stdout, stderr = take_screenshot(request)
            return ProcessRecord(request.argv, request.cwd, exit_code, stdout, stderr, 0)
        return run_process(request)

    return run
