#!/usr/bin/env python3
"""Read-only attribution of the retained AS-006 known-R1 trace."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-006-executable-weak-continuation-integrated-viability-r1")
OUT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-007-recovery-executability-integrated-viability-r1/AS007_AS006_TERMINAL_CAUSAL_ATTRIBUTION.json")
DECISION = EVIDENCE / "AS006_KNOWN_R1_57531938.decision.jsonl"
PLANNING = EVIDENCE / "AS006_KNOWN_R1_57531938.planning.jsonl"


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def candidate(row: dict) -> dict:
    c = row.get("final_candidate") or {}
    return {"capability": c.get("capability"), "params": c.get("params", {})}


def main() -> None:
    action_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    outcome_by_capability: Counter[str] = Counter()
    successful_reducers: list[dict] = []
    final_window: list[dict] = []
    checkpoints: dict[str, dict] = {}
    rows = 0
    ticks: list[int] = []
    with DECISION.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            rows += 1
            tick = int(row["tick"])
            ticks.append(tick)
            c = candidate(row)
            capability = str(c.get("capability"))
            action_counts[capability] += 1
            linkage = row.get("verified_outcome_linkage")
            if linkage:
                reason = str(linkage.get("reason"))
                result = "success" if linkage.get("success") else "failure"
                outcome_counts[result] += 1
                outcome_by_capability[f"{linkage.get('capability')}:{result}:{reason}"] += 1
                effects = linkage.get("effects") or {}
                if result == "success" and float(effects.get("fatigue", 0.0)) < 0.0:
                    successful_reducers.append({"tick": tick, "candidate": c, "linkage": linkage})
            if tick in {1927, 1928, 1929}:
                checkpoints[str(tick)] = {
                    "physiology": row.get("physiology"),
                    "active_ticks": row.get("active_ticks"),
                    "base_candidate": row.get("base_candidate"),
                    "final_candidate": row.get("final_candidate"),
                    "governance_decision": row.get("governance_decision"),
                    "critical_recovery_context": row.get("critical_recovery_context"),
                    "verified_outcome_linkage": linkage,
                    "policy_observation_fingerprint": row.get("policy_observation_fingerprint"),
                    "body_schema_generation": row.get("body_schema_generation"),
                }
            if tick >= 1800:
                final_window.append({
                    "tick": tick,
                    "physiology": row.get("physiology"),
                    "candidate": c,
                    "governance_decision": row.get("governance_decision"),
                    "critical_recovery_context": row.get("critical_recovery_context"),
                    "verified_outcome_linkage": linkage,
                    "policy_observation_fingerprint": row.get("policy_observation_fingerprint"),
                    "body_schema_generation": row.get("body_schema_generation"),
                })

    planning_counts: Counter[str] = Counter()
    planning_rows = 0
    if PLANNING.exists():
        with PLANNING.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                planning_rows += 1
                for profile in row.get("candidate_profiles", []):
                    classification = profile.get("profile", {}).get("classification")
                    if classification:
                        planning_counts[str(classification)] += 1

    value = {
        "schema": "AS007_AS006_TERMINAL_CAUSAL_ATTRIBUTION_V1",
        "directive": "UMBRA-AS-007",
        "source": {
            "decision_trace": str(DECISION),
            "decision_trace_sha256": file_sha(DECISION),
            "planning_trace": str(PLANNING),
            "planning_trace_sha256": file_sha(PLANNING) if PLANNING.exists() else None,
        },
        "retained_trace_shape": {"decision_rows": rows, "tick_min": min(ticks), "tick_max": max(ticks), "planning_rows": planning_rows},
        "modal_option_counts": dict(sorted(planning_counts.items())),
        "selected_action_counts": dict(sorted(action_counts.items())),
        "verified_outcome_counts": dict(sorted(outcome_counts.items())),
        "verified_outcome_by_capability": dict(sorted(outcome_by_capability.items())),
        "successful_fatigue_reducing_actions": {
            "count": len(successful_reducers),
            "last": successful_reducers[-1] if successful_reducers else None,
        },
        "terminal_window": {"start_tick": 1800, "end_tick": 1929, "rows": final_window},
        "exact_terminal_checkpoints": checkpoints,
        "attribution": {
            "retained_observation": "The trace establishes a terminal REST/not_at_rest outcome and the preceding NO_SAFE_ACTION decision. It does not alone prove which upstream recovery contract defect caused the state.",
            "terminal_sequence": ["tick_1927_REST_verified_failure_not_at_rest", "tick_1928_IDLE_no_safe_action", "tick_1929_REST_verified_failure_not_at_rest"],
            "causal_status": "SOURCE_AUDIT_REQUIRED",
        },
        "organism_execution": {"new_runs": 0, "new_ticks": 0, "retrospective_read_only": True},
    }
    atomic_json(OUT, value)
    print(json.dumps({k: value[k] for k in ("retained_trace_shape", "modal_option_counts", "selected_action_counts", "verified_outcome_counts", "successful_fatigue_reducing_actions", "exact_terminal_checkpoints")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
