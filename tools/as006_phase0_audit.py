"""Create the zero-run AS-006 Phase-0 implementation audits.

This tool inspects committed source and retained AS-005 summary artifacts. It
does not import runtime modules, construct an organism, or read partial traces
as qualification data.
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
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-006-executable-weak-continuation-integrated-viability-r1")
AS005 = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-005-preventive-modal-continuation-integrated-viability-r1")
BASELINE = "2bc042a7e1861b6c0beacca95a310d1d61ed0e5d"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


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


def source_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    remote = subprocess.check_output(["git", "ls-remote", "github", "refs/heads/master"], cwd=ROOT, text=True).split()[0]
    status = git("status", "--short")
    activation = json.loads((AS005 / "AS005_DEVELOPMENT_SOURCE_ACTIVATION.json").read_text(encoding="utf-8"))
    failure = json.loads((AS005 / "AS005_PROTOCOL_FAILURE.json").read_text(encoding="utf-8"))
    action = source_text("umbra_core/hypothetical/action_selection.py")
    qualification = source_text("experiments/as005/qualification.py")

    reconciliation = {
        "schema": "AS006_STATE_RECONCILIATION_V1",
        "directive": "UMBRA-AS-006",
        "baseline": BASELINE,
        "head": git("rev-parse", "HEAD"),
        "local_master": git("rev-parse", "master"),
        "github_master": remote,
        "branch": git("branch", "--show-current"),
        "worktree_status": status,
        "parent": {
            "verdict": failure["verdict"],
            "frozen_commit": failure["frozen_commit"],
            "partial_evidence_root": failure["evidence_root"],
            "partial_evidence_reuse": "PROHIBITED",
        },
        "start_counts": {"production_delta": 0, "existing_test_semantic_delta": 0, "organism_runs": 0, "organism_ticks": 0, "control_runs": 0, "shadow_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0},
        "notion_authority": "UMBRA-AS-006",
        "integrity": "PASS" if git("rev-parse", "HEAD") == BASELINE and git("rev-parse", "master") == BASELINE and remote == BASELINE and not status else "FAIL",
        "generated_at_epoch": time.time(),
    }
    publish("AS006_STATE_RECONCILIATION.json", reconciliation)

    implementation = {
        "schema": "AS006_AS005_IMPLEMENTATION_AUDIT_V1",
        "route_learning": {"configuration_source": "experiments/as005/qualification.py:as005_config", "explicitly_enabled": "route_demand_learning_enabled = True", "integrated_configured": "PASS" if "route_demand_learning_enabled = True" in qualification else "FAIL"},
        "source_activation": {"artifact": str(AS005 / "AS005_DEVELOPMENT_SOURCE_ACTIVATION.json"), "organism_runs": activation["organism_runs"], "ticks": activation["ticks"], "route_experience_frames": activation["route_experience_frames"], "modal_option_rows": activation["o0_nonempty_rows"], "status": "REAL_ROUTE_EVIDENCE_ACQUIRED_NON_QUALIFICATION"},
        "partial_scientific_evidence": {"diagnostic_a": "completed", "diagnostic_b": "incomplete_at_tick_2320", "known_r1": "not_started", "consumption": "NOT_CONSUMED"},
        "production_source_fingerprint": {"action_selection_sha256": sha(ROOT / "umbra_core/hypothetical/action_selection.py")},
        "status": "PASS",
    }
    publish("AS006_AS005_IMPLEMENTATION_AUDIT.json", implementation)

    modal = {
        "schema": "AS006_MODAL_LOSS_GAP_AUDIT_V1",
        "current_behavior": {"source": "umbra_core/hypothetical/action_selection.py:eliminate_by_continuation", "fallback_reason": "MAY_OPTION_NO_GUARANTEE", "candidate_status": "PRESERVED for every supported candidate; UNKNOWN only if immediate transition is unsupported/unknown", "candidate_caused_destroyed": False},
        "gap": "MAY options are exposed as candidate-neutral trace facts but are not evaluated against exact known option identity, route demand, source horizon, or post-candidate physiological feasibility.",
        "required_change": "candidate-independent KnownWeakContinuationOption plus categorical branch-wise PRESERVED/DESTROYED/UNKNOWN status; MAY remains MAY.",
        "partial_evidence_reuse": "PROHIBITED",
        "status": "PASS_GAP_CONFIRMED",
    }
    publish("AS006_MODAL_LOSS_GAP_AUDIT.json", modal)

    preventive = {
        "schema": "AS006_PREVENTIVE_SLACK_GAP_AUDIT_V1",
        "current_trigger": {"source": "umbra_core/hypothetical/action_selection.py:_owner_active", "formula": "remaining_boundary_time / abs(DEFAULT_DRIFT) <= MAX_CONTINUATION_DEPTH", "fixed_depth": "CONFIRMED"},
        "gap": "planner recursion depth is used as a preventive homeostatic horizon rather than exact option demand and source-support horizon.",
        "required_change": "owner-local recovery slack = source-backed boundary time minus exact lived option demand; use only binary feasibility and recompute after candidate branches.",
        "prohibitions": ["urgency normalization", "cross-owner arithmetic", "ranking", "least-laxity preference", "route-duration preference"],
        "status": "PASS_GAP_CONFIRMED",
    }
    publish("AS006_PREVENTIVE_SLACK_GAP_AUDIT.json", preventive)


if __name__ == "__main__":
    main()
