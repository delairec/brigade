import subprocess


def stop_process(process: subprocess.Popen, stop_signal: int, timeout_s: float) -> tuple[str, str]:
    process.send_signal(stop_signal)
    return process.communicate(timeout=timeout_s)
