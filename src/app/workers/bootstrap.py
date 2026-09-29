"""Idle worker entrypoint until durable jobs arrive in JOB-001."""

import signal
import time
from pathlib import Path

_running = True


def _stop(_signum: int, _frame: object) -> None:
    global _running
    _running = False


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    Path("/tmp/worker.ready").touch()
    while _running:
        time.sleep(1)


if __name__ == "__main__":
    main()
