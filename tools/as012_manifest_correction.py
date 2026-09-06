"""Append-only correction for the AS-012 manifest's transient SQLite sidecars."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-012-exact-entrypoint-boundedness-soak-causal-closure-r1")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, value: dict) -> str:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    os.replace(tmp, path)
    return sha(path)


def main() -> None:
    old = json.loads((EVIDENCE / "AS012_EVIDENCE_MANIFEST.json").read_text())
    retained = EVIDENCE / "retained-as012-boundedness-run"
    stable = []
    for path in sorted(retained.iterdir()):
        if path.is_file():
            stable.append({"name": str(path.relative_to(EVIDENCE)), "bytes": path.stat().st_size, "sha256": sha(path)})
    transient = [entry for entry in old["files"] if str(entry["name"]).endswith((".sqlite-shm", ".sqlite-wal")) and not (EVIDENCE / entry["name"]).exists()]
    correction = {"schema": "AS012_EVIDENCE_MANIFEST_CORRECTION_V1", "directive": "UMBRA-AS-012", "original_manifest_sha256": sha(EVIDENCE / "AS012_EVIDENCE_MANIFEST.json"), "reason": "SQLite WAL/SHM sidecars are transient and were not retained in the durable copied run; the stable SQLite and metric journal hashes are retained.", "transient_unretained_entries": transient, "stable_retained_entries": stable, "historical_manifest_unchanged": True}
    correction_sha = atomic(EVIDENCE / "AS012_EVIDENCE_MANIFEST_CORRECTION.json", correction)
    files = []
    for path in sorted(EVIDENCE.iterdir()):
        if path.name in {"AS012_EVIDENCE_MANIFEST_FINAL.json"} or not path.is_file():
            continue
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)})
    final = {"schema": "AS012_EVIDENCE_MANIFEST_FINAL_V2", "directive": "UMBRA-AS-012", "baseline": old["baseline"], "final_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "terminal_verdict": old["terminal_verdict"], "files": files, "retained_transient_sidecars": transient, "correction_sha256": correction_sha, "counts": old["counts"], "production_delta": 0, "no_retry_reseed": True, "historical_manifest_unchanged": True}
    final_sha = atomic(EVIDENCE / "AS012_EVIDENCE_MANIFEST_FINAL.json", final)
    print(json.dumps({"correction_sha256": correction_sha, "final_manifest_sha256": final_sha, "transient_sidecars": transient}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
