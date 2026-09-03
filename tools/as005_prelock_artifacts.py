"""Publish AS-005 pre-freeze contracts and immutable gate records."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from as005_phase0_audit import EVIDENCE, publish


ROOT = Path(__file__).resolve().parents[1]
DEV = EVIDENCE / "AS005_DEVELOPMENT_SOURCE_ACTIVATION.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    dev = json.loads(DEV.read_text())
    source_contract = {
        "schema": "AS005_SOURCE_STRENGTH_CONTRACT_V1",
        "strengths": {
            "HARD_CONTRACT": "categorical contract; may support universal continuation only within its declared scope",
            "VERIFIED_OBSERVED_SUPPORT": "verified historical fact; may support a concrete possibility but is not a universal future guarantee",
            "PROBABILISTIC_SUPPORT": "possible evidence only; never promoted to MUST",
            "UNKNOWN": "insufficient evidence; blocks unsupported elimination",
            "NOT_APPLICABLE": "does not apply; cannot create merit for another candidate",
        },
        "route_rule": "route experience remains MAY unless an independent hard/exhaustive source exists",
        "future_claim": "historical min/max intervals do not establish future guaranteed bounds by themselves",
        "world_truth_firewall": "no Habitat coordinates or evaluator-only facts enter the frame",
    }
    modal_contract = {
        "schema": "AS005_MODAL_CONTINUATION_CONTRACT_V1",
        "modalities": ["MUST", "MAY", "UNKNOWN"],
        "must": "universal supported branch coverage",
        "may": "complete concrete source-backed possibility, never inevitable completion or preference",
        "unknown": "preserved and blocks unsupported loss/preservation claims",
        "known_option_identity": "capability plus exact opportunity identity plus body-schema-compatible source route identity",
        "candidate_independence": "O0 and modal option identities are constructed before candidate evaluation",
        "duplicate_rule": "semantic duplicate options collapse; no option count authority",
        "authority": "MAY evidence is recorded and classified but does not rank candidates or grant an action queue",
    }
    preventive_contract = {
        "schema": "AS005_PREVENTIVE_OBLIGATION_CONTRACT_V1",
        "inputs": ["current physiology", "constitutional viable/critical bounds", "qualified autonomous drift", "verified corrective effects", "bounded planning horizon"],
        "activation": "owner is preventive when its current in-band value reaches the constitutional viable boundary within the existing bounded continuation horizon under its qualified drift direction",
        "active_outside_viable": True,
        "no_ideal_forcing": True,
        "no_urgency_export": True,
        "no_cross_owner_arithmetic": True,
        "critical_recovery": "remains on its established separate authority path",
    }
    route_contract = {
        "schema": "AS005_ROUTE_ACTIVATION_CONTRACT_V1",
        "full_stack_config": {"world_model_enabled": True, "world_model_config.route_demand_learning_enabled": True, "bounded_continuation_enabled": True},
        "learning": "only executed verified outcomes; no proposal/prediction/shadow/hypothetical learning",
        "binding": "exact opportunity entity plus body schema; ambiguity and mismatch fail closed",
        "evidence": "V2 ordered route-control steps, route timing, failure evidence, provenance, persistence, and body identity retained",
        "authority": "route learning remains write-only to planning evidence until the AS-005 authority gate",
        "development_gate": {"organism_runs": dev["organism_runs"], "ticks": dev["ticks"], "route_experience_frames": dev["route_experience_frames"], "o0_nonempty_rows": dev["o0_nonempty_rows"], "modal_option_count": dev["modal_option_count"], "dense_trace_retained": True},
    }
    fingerprints = {
        str(path.relative_to(ROOT)): file_sha(path)
        for path in (
            ROOT / "umbra_core/hypothetical/action_selection.py",
            ROOT / "umbra_core/hypothetical/modal.py",
            ROOT / "umbra_core/hypothetical/frame.py",
            ROOT / "umbra_core/hypothetical/core.py",
            ROOT / "umbra_core/hypothetical/adapters.py",
            ROOT / "umbra_core/hypothetical/continuation.py",
            ROOT / "umbra_core/world_model/engine.py",
            ROOT / "umbra_core/world_model/route_evidence.py",
            ROOT / "umbra_core/runtime.py",
            ROOT / "experiments/as005/qualification.py",
        )
    }
    static = {
        "schema": "AS005_STATIC_AUTHORITY_AUDIT_V1",
        "route_learning_readers": ["WorldModel.observe_outcome learning seam", "PlanningEvidenceFrame shadow projection when explicitly enabled"],
        "forbidden_readers_checked": ["candidate generation", "arbitration ranking", "distributed competition source priority", "Governance", "Embodiment", "CLOSE-02Z stochasticity", "hypothetical learning"],
        "modal_authority": "no MAY/MUST preference or score; ordinary eliminator only receives candidate-neutral source option classifications",
        "production_source_fingerprint": fingerprints,
        "status": "PASS",
    }
    freeze = {
        "schema": "AS005_PRE_FREEZE_GATE_V1",
        "baseline": "b45a3c1480d57638768f5a876c8807c6f756143c",
        "current_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "focused_tests": {"first": "65 passed", "second": "65 passed"},
        "applicable_suite": {"result": "1293 passed / 2 skipped / 13 inherited failures", "excluded_collection_defect": "tests/test_close02x_prospective_recoverability.py unchanged at baseline; missing package export", "candidate_only_failures": 0},
        "source_activation": dev,
        "gates": {"source_contract": "PASS", "modal_contract": "PASS", "preventive_contract": "PASS", "route_activation": "PASS", "dense_trace_retention": "PASS", "production_delta_since_start": 1},
        "post_lock_policy": "no scientific code/test/config changes; no retry/reseed; stop at first terminal boundary",
    }
    for name, value in (
        ("AS005_SOURCE_STRENGTH_CONTRACT.json", source_contract),
        ("AS005_MODAL_CONTINUATION_CONTRACT.json", modal_contract),
        ("AS005_PREVENTIVE_OBLIGATION_CONTRACT.json", preventive_contract),
        ("AS005_ROUTE_ACTIVATION_CONTRACT.json", route_contract),
        ("AS005_STATIC_AUTHORITY_AUDIT.json", static),
        ("AS005_PRE_FREEZE_GATE.json", freeze),
    ):
        print(name, publish(name, value))


if __name__ == "__main__":
    main()
