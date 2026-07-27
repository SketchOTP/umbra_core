"""Linux process identity stronger than PID alone."""
from __future__ import annotations
from pathlib import Path
def process_identity(pid: int) -> str | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split()
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return f"{boot_id}:{pid}:{fields[21]}"
    except (FileNotFoundError, IndexError, PermissionError):
        return None
def identity_matches(pid: int, expected: str) -> bool:
    return process_identity(pid) == expected
