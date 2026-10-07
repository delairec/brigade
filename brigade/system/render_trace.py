import shlex

from brigade.system.process_trace import CUT, EXITED, NOT_FOUND, SPAWNED, TIMED_OUT, ProcessTrace

ENDINGS = {
    EXITED: lambda trace: f"exit {trace.exit_code} in {trace.duration_ms} ms",
    TIMED_OUT: lambda trace: f"timed out after {trace.duration_ms} ms",
    NOT_FOUND: lambda trace: "not on PATH",
    CUT: lambda trace: f"cut after {trace.duration_ms} ms",
    SPAWNED: lambda trace: f"spawned pid {trace.pid}",
}


def render_trace(trace: ProcessTrace) -> str:
    return f"ran {shlex.join(trace.argv)}, {ENDINGS[trace.outcome](trace)}"
