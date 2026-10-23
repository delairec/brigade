import os


def signal_itself(stop_signal: int) -> None:
    os.kill(os.getpid(), stop_signal)
