import time


def elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
