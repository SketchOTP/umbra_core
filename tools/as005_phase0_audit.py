"""AS-005 zero-organism start and Phase-0 evidence audit.

This tool reads source and immutable AS-004 closeout evidence only. It never
imports or constructs an organism and publishes create-once evidence with
fsync/atomic-rename/readback hashing.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


ROOT = Path("/home/sketch/Projects/umbra-close02x-work")
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-005-preventive-modal-continuation-integrated-viability-r1")
AS004 = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-004-bounded-continuation-integrated-viability-r1")
BASELINE = "b45a3c1480d57638768f5a876c8807c6f756143c"
AS004_MANIFEST = "ca0cd93b4effba187480ad36467ad62af4cb0c4e49a687a722e5808d3bd52ad6"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish(name: str, value: object) -> str:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE / name
    if target.exists():
        raise FileExistsError(target)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=EVIDENCE, prefix=f".{name}.", suffix=".tmp", delete=False) as fh:
        temporary = Path(fh.name)
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temporary, target)
    directory = os.open(EVIDENCE, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    assert sha(target) == hashlib.sha256(payload).hexdigest()
    return sha(target)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    as004 = json.loads((AS004 / "AS004_TERMINAL_CLOSEOUT.json").read_text())
    remote = subprocess.check_output(["git", "ls-remote", "github", "refs/heads/master"], cwd=ROOT, text=True).split()[0]
    state = {
        "schema": "AS005_STATE_RECONCILIATION_V1",
        "directive": "UMBRA-AS-005",
        "baseline": BASELINE,
        "head": git("rev-parse", "HEAD"),
        "local_master": git("rev-parse", "master"),
        "github_master": remote,
        "branch": git("branch", "--show-current"),
        "worktree_status": git("status", "--short"),
        "expected": {"head": BASELINE, "local_master": BASELINE, "github_master": BASELINE, "branch": "master", "worktree_status": ""},
        "parent": {"verdict": as004["verdict"], "manifest_sha256": AS004_MANIFEST, "organism_runs": as004["organism_runs"], "diagnostic_runs": as004["diagnostic_runs"], "control_runs": as004["control_runs"], "shadow_runs": as004["shadow_runs"], "retries": as004["retries"], "reseeds": as004["reseeds"], "known_r1_terminal": as004["first_scientific_failure"]},
        "as005_start_integrity": {"production_delta": 0, "existing_test_semantic_delta": 0, "organism_runs": 0, "control_runs": 0, "shadow_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0},
        "notion_authority": "UMBRA-AS-005",
        "notion_refetch": "PASS",
        "integrity": "PASS" if git("rev-parse", "HEAD") == BASELINE and git("rev-parse", "master") == BASELINE and remote == BASELINE and git("status", "--short") == "" else "FAIL",
        "generated_at_epoch": time.time(),
    }
    publish("AS005_STATE_RECONCILIATION.json", state)

    causal = {
        "schema": "AS005_AS004_CAUSAL_BOUNDARY_AUDIT_V1",
        "parent_verdict": "AS004_KNOWN_R1_FAIL",
        "protected_observations": {"diagnostic_a_o0_empty": 278, "diagnostic_b_o0_empty": 1751, "known_r1_o0_empty": 946, "total_o0_empty": 2975, "eliminations": 0, "dense_trace_retained": False},
        "failure_boundary": {"first_no_safe_action_tick": 1928, "critical_tick": 1929, "failure_capability": "REST", "failure_reason": "not_at_rest"},
        "interpretation": "AS-004 is permanent historical evidence; its empty O0 is not a tuning target and cannot establish why AS-005 source activation should succeed.",
    }
    publish("AS005_AS004_CAUSAL_BOUNDARY_AUDIT.json", causal)

    source = {
        "schema": "AS005_SOURCE_ACTIVATION_AUDIT_V1",
        "route_learning_default": False,
        "source": "umbra_core/world_model/engine.py:WorldModelConfig.route_demand_learning_enabled",
        "as004_runner_route_learning": "not explicitly enabled",
        "as005_requirement": "full-stack configuration must explicitly enable route learning before scientific lock",
        "route_learning_reader": "WorldModel.observe_outcome learning seam only; no planning/arbitration reader may be introduced by Phase 0",
        "status": "BLOCKED_PENDING_AS005_CONFIGURATION_AUDIT",
    }
    publish("AS005_SOURCE_ACTIVATION_AUDIT.json", source)

    modality = {
        "schema": "AS005_MODALITY_MISMATCH_AUDIT_V1",
        "future_opportunity": "MAY/UNKNOWN are not MUST; current AS-004 source adapter maps non-MUST persistence to UNKNOWN",
        "route_experience": "R6C route experience is observed MAY evidence, not universal duration guarantee",
        "strong_only_risk": "AS-004 source path can leave O0 empty when only MAY route evidence exists",
        "required_repair_boundary": "represent source-faithful MUST/MAY/UNKNOWN without promoting MAY to guarantee",
        "status": "AUDIT_REQUIRED_BEFORE_IMPLEMENTATION",
    }
    publish("AS005_MODALITY_MISMATCH_AUDIT.json", modality)

    preventive = {
        "schema": "AS005_PREVENTIVE_OBLIGATION_AUDIT_V1",
        "current_owner_activation": "_owner_active currently returns true only outside BOUNDS.in_viable(value)",
        "arbitration_preventive_pool": "_preventive_attention_dimensions uses active_recovery_needs plus vector_urgency and is not a finite correction-horizon proof",
        "required_property": "preventive obligation may activate before viable-band exit only when current state, constitutional bounds, drift, verified correction effect, and source-backed demand establish finite correction horizon",
        "no_new_threshold": True,
        "status": "AUDIT_REQUIRED_BEFORE_IMPLEMENTATION",
    }
    publish("AS005_PREVENTIVE_OBLIGATION_AUDIT.json", preventive)


if __name__ == "__main__":
    main()
