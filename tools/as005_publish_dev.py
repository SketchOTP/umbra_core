"""Durably publish the completed AS-005 development source-activation traces."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from as005_phase0_audit import EVIDENCE, publish


def durable_copy(source: Path, name: str) -> str:
    target = EVIDENCE / name
    if target.exists():
        raise FileExistsError(target)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as inp, tempfile.NamedTemporaryFile(dir=EVIDENCE, prefix=f".{name}.", suffix=".tmp", delete=False) as out:
        temporary = Path(out.name)
        shutil.copyfileobj(inp, out)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, target)
    directory = os.open(EVIDENCE, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return hashlib.sha256(target.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: as005_publish_dev.py DEV_DIR")
    source = Path(sys.argv[1])
    files = sorted(source.glob("AS005_SOURCE_ACTIVATION_R0_45878900.*jsonl"))
    if len(files) != 2:
        raise SystemExit(f"expected two source-activation traces, found {files}")
    hashes = {path.name: durable_copy(path, f"AS005_DEVELOPMENT_{path.name.split('.', 1)[1]}") for path in files}
    decision = next(path for path in files if path.suffix == ".jsonl" and "decision" in path.name)
    planning = next(path for path in files if path.suffix == ".jsonl" and "planning" in path.name)
    rows = [json.loads(line) for line in decision.read_text(encoding="utf-8").splitlines() if line.strip()]
    shadow = [json.loads(line) for line in planning.read_text(encoding="utf-8").splitlines() if line.strip()]
    continuation = [((row.get("distributed_competition") or {}).get("continuation") or {}) for row in rows]
    summary = {
        "schema": "AS005_DEVELOPMENT_SOURCE_ACTIVATION_V1",
        "seed": 45878900,
        "regime": "R0",
        "horizon": 500,
        "organism_runs": 1,
        "ticks": 500,
        "terminal": "completed",
        "route_experience_frames": len(shadow),
        "planning_frames": len(shadow),
        "o0_nonempty_rows": sum(1 for row in continuation if int(row.get("root_size", 0)) > 0),
        "modal_option_count": sum(len(row.get("modal_options") or ()) for row in continuation),
        "candidate_classification_rows": sum(len(row.get("classifications") or ()) for row in continuation),
        "modal_profile_count": sum(len(row.get("candidate_profiles") or ()) for row in shadow),
        "modal_classification_counts": {
            cls: sum(1 for row in shadow for profile in row.get("candidate_profiles") or () if ((profile.get("profile") or {}).get("classification") == cls))
            for cls in ("STRONG_MUST_CONTINUATION", "STRONG_MAY_CONTINUATION", "WEAK_MAY_CONTINUATION", "NO_CONTINUATION", "UNKNOWN")
        },
        "trace_hashes": hashes,
        "interpretation": "Development-only source activation; MAY evidence is not promoted to guarantee or action-selection authority.",
    }
    print(publish("AS005_DEVELOPMENT_SOURCE_ACTIVATION.json", summary))


if __name__ == "__main__":
    main()
