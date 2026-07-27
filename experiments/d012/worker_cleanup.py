"""Identity-safe cleanup for disposable D-012 workers."""
from __future__ import annotations

import os
import signal
import time

from .failure_codes import SupervisionError
from .process_identity import identity_matches


def wait_dead(pid: int, identity: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            waited, _ = os.waitpid(pid, os.WNOHANG)
            if waited == pid:
                return
        except ChildProcessError:
            if not identity_matches(pid, identity):
                return
        if not identity_matches(pid, identity):
            return
        time.sleep(0.01)
    raise SupervisionError("ORGANISM_EXIT_UNEXPECTED", "worker_still_alive")


def terminate_worker(
    pid: int,
    identity: str,
    *,
    force: bool = False,
    timeout: float = 5.0,
) -> None:
    if not identity_matches(pid, identity):
        return
    os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
    wait_dead(pid, identity, timeout)
