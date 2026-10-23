import os

from brigade.system.process_trace import ProcessTrace
from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process

INHERITED_ENVIRONMENT = os.environ


def _keep_no_trace(trace: ProcessTrace) -> None:
    pass


def run_process_without_trail(request: ProcessRequest) -> ProcessRecord:
    return run_process(request, _keep_no_trace, INHERITED_ENVIRONMENT)
