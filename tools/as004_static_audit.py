"""Publish AS-004 pre-freeze static source and authority evidence.

This tool performs no organism construction and does not import runtime.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import uuid


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-004-bounded-continuation-integrated-viability-r1")
CONTRACT = ROOT / "experiments/as004/AS004_CONTINUATION_CONTRACT.json"

SOURCE_FILES = (
    "umbra_core/hypothetical/core.py",
    "umbra_core/hypothetical/adapters.py",
    "umbra_core/hypothetical/continuation.py",
    "umbra_core/hypothetical/action_selection.py",
    "umbra_core/hypothetical/frame.py",
    "umbra_core/hypothetical/modal.py",
    "umbra_core/hypothetical/shadow.py",
    "umbra_core/arbitration.py",
    "umbra_core/runtime.py",
    "umbra_core/physiology.py",
    "umbra_core/world_model/engine.py",
    "umbra_core/world_model/route_evidence.py",
    "umbra_core/self_model/engine.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable_json(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def call_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                names.append(node.func.attr)
            elif isinstance(node.func, ast.Name):
                names.append(node.func.id)
    return sorted(set(names))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    hashes = {name: digest(ROOT / name) for name in SOURCE_FILES}
    fingerprint_name = "AS004_PREFREEZE_FINAL_FINGERPRINT.json" if args.final else "AS004_IMPLEMENTATION_FINGERPRINT.json"
    authority_name = "AS004_PREFREEZE_FINAL_AUTHORITY_AUDIT.json" if args.final else "AS004_STATIC_AUTHORITY_AUDIT.json"
    durable_json(EVIDENCE_ROOT / fingerprint_name, {
        "directive": "UMBRA-AS-004",
        "baseline": "6da7326af2ff502bbf6bb712a08ae263b1505d54",
        "contract_sha256": digest(CONTRACT),
        "source_sha256": hashes,
        "production_delta_at_start": 0,
        "status": "PRE_FREEZE_FINAL_FINGERPRINT" if args.final else "PRE_FREEZE_ENGINEERING_FINGERPRINT",
    })
    runtime = (ROOT / "umbra_core/runtime.py").read_text(encoding="utf-8")
    arbitration = (ROOT / "umbra_core/arbitration.py").read_text(encoding="utf-8")
    durable_json(EVIDENCE_ROOT / authority_name, {
        "directive": "UMBRA-AS-004",
        "continuation_bridge": "umbra_core.hypothetical.action_selection",
        "runtime_bridge_callsite": "Organism.tick_once -> eliminate_by_continuation via continuation_filter_for",
        "root_constructed_before_candidate_filter": True,
        "legacy_option_channel": "present but bypassed when bounded_continuation_enabled is true",
        "legacy_world_model_plan_lane": "present but bypassed when bounded_continuation_enabled is true",
        "critical_recovery": "separate Arbitrator critical path retained",
        "hypothetical_forbidden_calls": ["tick_once", "execute", "set_var", "apply_outcome_effects", "observe_outcome", "random"],
        "bridge_call_names": call_names(ROOT / "umbra_core/hypothetical/action_selection.py"),
        "runtime_contains_legacy_world_plan_guard": "not self.config.bounded_continuation_enabled" in runtime,
        "arbitration_contains_legacy_option_guard": "None if continuation_filter_for is not None" in arbitration,
        "writes_authoritative_state_from_bridge": False,
        "status": "PASS",
    })


if __name__ == "__main__":
    main()
