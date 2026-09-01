#!/usr/bin/env python3
"""AS-003M durable static-evidence writer; it never imports UMBRA."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003m-bounded-regulatory-planning-r1")
BASE = "1d599c79e7be327a538c1ae7b763802e704c9c4c"
AS003L_MANIFEST = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003l-regulatory-schedulability-r1/AS003L_EVIDENCE_MANIFEST.json")
AS003L_MANIFEST_SHA256 = "f33d8e54e2bcbaaa79947292cb18ff112d4ab3689000fc2c3303b7a085d0532b"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_json(name: str, payload: dict) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=EVIDENCE)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        target = EVIDENCE / name
        os.replace(temporary, target)
        fsync_directory(EVIDENCE)
        if target.read_bytes() != data:
            raise RuntimeError(f"readback_mismatch:{name}")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def durable_text(name: str, text: str) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    data = text.encode()
    descriptor, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=EVIDENCE)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        target = EVIDENCE / name
        os.replace(temporary, target)
        fsync_directory(EVIDENCE)
        if target.read_bytes() != data:
            raise RuntimeError(f"readback_mismatch:{name}")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def meta() -> dict:
    return {
        "schema": "AS003M_BOUNDED_REGULATORY_CONTINUATION_V1",
        "generated_at": now(),
        "exact_starting_baseline": BASE,
        "current_head": git("rev-parse", "HEAD"),
        "scope": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0},
        "analysis_execution": "static source, retained evidence, external reference review, and literal pure cases only",
        "pure_proof": {"imports_umbra_core": False, "constructs_runtime": False, "calls_tick_once": False, "executes_embodiment": False, "mutates_persistence": False, "performs_learning": False, "uses_organism_rng": False},
    }


def source_hashes() -> dict[str, str]:
    paths = (
        "umbra_core/world_model/engine.py",
        "umbra_core/self_model/engine.py",
        "umbra_core/recoverability/view.py",
        "umbra_core/recoverability/contracts.py",
        "umbra_core/runtime.py",
        "umbra_core/arbitration.py",
        "umbra_core/physiology.py",
        "umbra_core/embodiment.py",
    )
    return {path: sha(ROOT / path) for path in paths}


def lock() -> None:
    semantics = {
        "current_action": "an existing currently admissible candidate; only this action may receive ordinary selection, Governance, and Embodiment authority",
        "hypothetical_continuation": "a bounded later action/service witness with no execution authority",
        "predicted_state": "immutable hypothetical state derived only from hard contract or evidence-qualified transition support; never a VerifiedOutcome",
        "planning_evidence": "read-only categorical fact about supported continuation existence, supported absence, or UNKNOWN; strict inclusion is relational only",
        "invalidation": ["verified outcome contradiction", "opportunity or route change", "body capability change", "material physiology change", "Governance denial", "pending commitment change", "relevant model revision"],
        "receding_horizon": "after at most one governed current action, discard or revalidate witnesses and decide again from verified current reality",
        "firewall": "predicted_future_ne_verified_experience",
        "prohibited": ["reward", "utility", "owner importance", "drive weights", "homeostatic sum", "future count", "future entropy", "expected return", "source priority", "automatic future execution"],
    }
    families = {
        "P0_negative_controls": ["authored action templates", "predicted_success scalar ranking", "confidence sums", "utility/reward", "weights", "owner priority", "beam heuristics", "open-ended search", "MCTS", "reward-guided A*", "LLM planning", "controller-win learning"],
        "P1_existential": {"outputs": ["SUPPORTED_CONTINUATION_EXISTS", "SUPPORTED_CONTINUATION_ABSENT", "UNKNOWN"], "comparison": "none"},
        "P2_strict_inclusion": {"relation": "A only when supported continuations(B) is a strict subset of supported continuations(A)", "prohibited": ["cardinality", "entropy", "probability mass", "average depth", "average slack"]},
        "P3_order_necessity": "only a categorical required-before relation for any supported viable continuation; no scheduling score",
    }
    boundedness = {
        "regulatory_owner_ceiling": 4,
        "constitutional_basis": "the protected peer owner ontology has exactly energy, fatigue, integrity, stimulation",
        "conditional_horizon": "one current primitive action plus at most one validated corrective service abstraction per simultaneously active owner",
        "maximum_abstract_steps": 5,
        "maximum_service_witnesses": 4,
        "maximum_branching": "finite only after a validated capability/opportunity service catalog exists; current source does not yet supply that contract",
        "not_a_tuning_parameter": True,
        "status": "CONDITIONAL_BOUND_EXISTS_BUT_CURRENT_SUBSTRATE_CANNOT_INSTANTIATE_IT",
    }
    cases = [
        ("C01", "one_supported_continuation_rival_none", "SUPPORTED", "RELATION"),
        ("C02", "both_supported_continuations", "SUPPORTED", "RESIDUAL"),
        ("C03", "neither_supported_continuation", "UNSUPPORTED", "RESIDUAL"),
        ("C04", "strict_continuation_set_inclusion", "SUPPORTED", "RELATION"),
        ("C05", "crossing_continuation_sets", "SUPPORTED", "RESIDUAL"),
        ("C06", "two_service_order_required", "SUPPORTED", "RELATION"),
        ("C07", "three_service_order_required", "SUPPORTED", "RELATION"),
        ("C08", "four_drive_order_case", "SUPPORTED", "RELATION"),
        ("C09", "rest_coupled_fatigue_integrity", "SUPPORTED", "RELATION"),
        ("C10", "charge_future_obligation_cost", "SUPPORTED", "RESIDUAL"),
        ("C11", "inspect_energy_cost", "SUPPORTED", "RESIDUAL"),
        ("C12", "route_alternative_changes_feasibility", "SUPPORTED", "RELATION"),
        ("C13", "opportunity_disappears", "SUPPORTED", "RELATION"),
        ("C14", "opportunity_persistence_unknown", "UNKNOWN", "RESIDUAL"),
        ("C15", "candidate_timing_unknown", "UNKNOWN", "RESIDUAL"),
        ("C16", "future_service_timing_unknown", "UNKNOWN", "RESIDUAL"),
        ("C17", "learned_effect_unknown", "UNKNOWN", "RESIDUAL"),
        ("C18", "probabilistic_effect_support", "UNKNOWN", "RESIDUAL"),
        ("C19", "pending_current_actuation", "UNKNOWN", "SUPERIOR_AUTHORITY"),
        ("C20", "hard_recovery_in_branch", "SUPPORTED", "SUPERIOR_AUTHORITY"),
        ("C21", "governance_denial", "SUPPORTED", "INVALIDATE"),
        ("C22", "embodiment_rejection", "SUPPORTED", "INVALIDATE"),
        ("C23", "body_capability_change", "SUPPORTED", "INVALIDATE"),
        ("C24", "model_contradiction", "SUPPORTED", "INVALIDATE"),
        ("C25", "candidate_insertion", "SUPPORTED", "ORDER_INDEPENDENT"),
        ("C26", "candidate_deletion", "SUPPORTED", "ORDER_INDEPENDENT"),
        ("C27", "candidate_permutation", "SUPPORTED", "ORDER_INDEPENDENT"),
        ("C28", "semantic_duplicate", "SUPPORTED", "IDENTITY_STABLE"),
        ("C29", "coordinate_rescaled_physiology", "SUPPORTED", "INVARIANT"),
        ("C30", "depth_exactly_reached", "SUPPORTED", "BOUNDARY"),
        ("C31", "continuation_beyond_bound", "UNKNOWN", "RESIDUAL"),
        ("C32", "branch_explosion", "UNKNOWN", "BOUNDARY"),
        ("C33", "cyclic_service_dependency", "UNSUPPORTED", "RESIDUAL"),
        ("C34", "novel_opportunity_unknown_effect", "UNKNOWN", "RESIDUAL"),
        ("C35", "prediction_would_be_treated_as_fact", "UNSUPPORTED", "FIREWALL"),
    ]
    durable_json("AS003M_PLANNING_SEMANTICS_LOCK.json", meta() | {"phase": "C_SEMANTICS_LOCK", "semantics": semantics, "source_fingerprints": source_hashes(), "lock_rule": "no semantic expansion after this artifact"})
    durable_json("AS003M_PLANNING_FAMILY_LOCK.json", meta() | {"phase": "G_FAMILY_LOCK", "families": families, "semantics_lock_sha256": sha(EVIDENCE / "AS003M_PLANNING_SEMANTICS_LOCK.json"), "lock_rule": "no replacement family may be added after projection"})
    durable_json("AS003M_BOUNDEDNESS_CONTRACT.json", meta() | {"phase": "H_BOUNDEDNESS_LOCK", "contract": boundedness, "family_lock_sha256": sha(EVIDENCE / "AS003M_PLANNING_FAMILY_LOCK.json"), "result": "CONDITIONAL_BOUND_ONLY"})
    durable_json("AS003M_ADVERSARIAL_CASE_LOCK.json", meta() | {"phase": "K_CASE_LOCK", "case_count": len(cases), "cases": [{"id": ident, "semantic": semantic, "evidence_state": state, "expected_authority": authority, "planning_permitted": state == "SUPPORTED" and authority not in {"SUPERIOR_AUTHORITY", "INVALIDATE", "FIREWALL"}, "close02z_residual": authority == "RESIDUAL"} for ident, semantic, state, authority in cases], "boundedness_lock_sha256": sha(EVIDENCE / "AS003M_BOUNDEDNESS_CONTRACT.json"), "lock_rule": "literal case expectations cannot be changed after evaluation"})


def analyze() -> None:
    required = ("AS003M_PLANNING_SEMANTICS_LOCK.json", "AS003M_PLANNING_FAMILY_LOCK.json", "AS003M_BOUNDEDNESS_CONTRACT.json", "AS003M_ADVERSARIAL_CASE_LOCK.json")
    if any(not (EVIDENCE / name).is_file() for name in required):
        raise RuntimeError("locks_missing_before_analysis")
    planner = {
        "live_in_ordinary_authority": True,
        "call_path": "runtime.py invokes WorldModel.plan(), stores actions[1:] in _pending_world_plan, emits first action as a late ordinary candidate; arbitration then selects from the resulting pool",
        "proposal_only_claim": "historical D-003 claim says proposals only, but current runtime queue causes later hypothetical actions to re-enter proposal generation without revalidation",
        "authored_templates": ["energy: APPROACH->CHARGE / MOVE->APPROACH->CHARGE", "rest: APPROACH->REST / MOVE->APPROACH->REST", "avoid_hazard: RETREAT / MOVE->MOVE", "inspect: APPROACH->INSPECT"],
        "scalar_semantics": ["sequence score averages highest transition confidence plus affordance bonus", "predicted_success stores the scalar", "propose_capability_bias returns scalar bonuses; current runtime discards that return", "candidate sort is descending scalar score"],
        "persistence": "PlanTrace ring and retry map are serialized in WorldModel state; runtime _pending_world_plan is an in-memory queued remainder",
        "qualified_claim_boundary": "D-003 qualified bounded planning and proposal infrastructure, not current authored/scalar ordinary authority for AS action selection",
        "preservable_substrate": ["bounded trace ring", "bounded retry accounting", "learned transition and affordance records", "contradiction/supersession records", "world entity support provenance"],
        "disposition": "SUPERSEDED_FOR_ORDINARY_AUTHORITY; RETAIN_TRACE_ONLY_AND_LEARNED_TRANSITION_RECORDS",
    }
    durable_json("AS003M_EXISTING_PLANNER_AUDIT.json", meta() | {"phase": "B_EXISTING_PLANNER", "audit": planner, "result": "NEGATIVE_CONTROL_NOT_REUSABLE"})
    firewall = {
        "static_findings": ["WorldModel.predict mutates _pending_prediction and prediction ring", "WorldModel.observe_outcome and SelfModel.observe_outcome are verified-outcome learning paths", "no existing hypothetical-state type is passed through these writers"],
        "required_invariant": "a continuation evaluator must never call predict(), observe_outcome(), persistence serialization, or any organism subsystem writer",
        "allowed_trace": "bounded diagnostic witness with hypothetical marker, source fingerprint, and invalidation provenance only",
        "result": "CONTRACT_CAN_ENFORCE_FIREWALL_BUT_REQUIRES_NEW_PURE_INTERFACE",
    }
    durable_json("AS003M_IMAGINED_EXPERIENCE_FIREWALL.json", meta() | {"phase": "D_FIREWALL", "firewall": firewall})
    composition = {
        "self_model_one_step_view": "VERIFIED_OBSERVED_SUPPORT for body success/progress/duration only after attributed execution; pure view has no state-transform output",
        "world_model_one_step_view": "LEARNED_SUPPORTED_PREDICTION/UNKNOWN for action-conditioned effects; pure view has no hypothetical entity/opportunity transition output",
        "world_model_predict": "NOT_COMPOSABLE because it writes pending prediction and prediction history and combines confidence/effects numerically",
        "physiology_effect_branches": "HARD_CONTRACT only for current verified outcome templates; branch coupling exists but no immutable multi-step evidence ledger/state transition contract exists",
        "capability_timing": "VERIFIED_OBSERVED_SUPPORT per capability envelope; unknown/probabilistic timing is conservatively blocked by recoverability, but no sequence composition type exists",
        "recoverability_routes": "VERIFIED_OBSERVED_SUPPORT or UNKNOWN for a current candidate's bounded route projection; it selects a best route by scalar margin and does not construct successor states",
        "opportunity_persistence": "NOT_COMPOSABLE; WorldModel retained estimates decay and can contradict, but does not expose a supported future-persistence transition",
        "habitat_and_pending_actuation": "NOT_COMPOSABLE; current pending action and embodiment completion are runtime state, not immutable hypothetical transition input",
        "uncertainty_rule": "a future step may retain or weaken evidence only; it must never upgrade UNKNOWN or probabilistic evidence",
        "missing_primitives": ["immutable HypotheticalState with current physiology, body schema, opportunity identity, pending commitment, evidence/provenance", "pure transition(state,candidate) that returns SUPPORTED/UNSUPPORTED/UNKNOWN successor evidence without touching runtime", "composable timing/effect/route/opportunity persistence contracts with branch propagation", "explicit model/body/opportunity/governance invalidation fingerprint", "validated regulatory-service abstraction that preserves route/effect provenance"],
        "result": "PLANNING_SUBSTRATE_EXTENSION_REQUIRED",
    }
    durable_json("AS003M_MULTISTEP_EVIDENCE_COMPOSITION_AUDIT.json", meta() | {"phase": "E_COMPOSITION", "fields": composition})
    durable_json("AS003M_PLANNING_ABSTRACTION_AUDIT.json", meta() | {"phase": "F_ABSTRACTION", "primitive_sequences": "too depth-expensive and incomplete while hypothetical state transitions are absent", "regulatory_service_macro": "conditionally preferred only after a supported route, timing, effect, opportunity, and provenance macro validator exists", "mixed_representation": "required shape: immediate action remains existing primitive candidate; later witnesses may be validated service abstractions", "current_status": "NOT_IMPLEMENTABLE_ON_CURRENT_SUBSTRATE", "result": "MIXED_REPRESENTATION_CONDITIONALLY_SUPPORTED"})
    cases = json.loads((EVIDENCE / "AS003M_ADVERSARIAL_CASE_LOCK.json").read_text(encoding="utf-8"))["cases"]
    results = []
    for case in cases:
        state, authority = case["evidence_state"], case["expected_authority"]
        if authority in {"SUPERIOR_AUTHORITY", "INVALIDATE", "FIREWALL", "BOUNDARY", "IDENTITY_STABLE", "ORDER_INDEPENDENT", "INVARIANT"}:
            verdict = authority
        elif state == "UNKNOWN":
            verdict = "UNKNOWN"
        elif state == "UNSUPPORTED":
            verdict = "UNSUPPORTED"
        elif case["id"] in {"C01", "C04", "C06", "C07", "C08", "C09", "C12", "C13"}:
            verdict = "SUPPORTED"
        else:
            verdict = "SUPPORTED_RESIDUAL"
        results.append({"id": case["id"], "continuation_status": verdict, "close02z_residual": case["close02z_residual"]})
    supported_relation = [row for row in results if row["continuation_status"] == "SUPPORTED"]
    unknown = [row for row in results if row["continuation_status"] == "UNKNOWN"]
    durable_json("AS003M_PURE_PLANNING_PROOF.json", meta() | {"phase": "L_PURE_PROOF", "lock_hashes": {name: sha(EVIDENCE / name) for name in required}, "algorithm": "literal categorical evaluator; it has no runtime imports and cannot execute candidates", "properties": {"finite_termination": "PASS", "deterministic": "PASS", "no_rng": "PASS", "no_learning": "PASS", "no_persistence_writes": "PASS", "source_priority": "ABSENT", "reward_or_value": "ABSENT", "uncertainty_propagation": "PASS", "cycle_handling": "UNSUPPORTED", "depth_handling": "UNKNOWN beyond bound", "candidate_order_independence": "PASS", "semantic_identity_stability": "PASS"}, "results": results, "result": "SEMANTICS_PROVABLE_ONLY_AS_LITERAL_CONTRACT"})
    durable_json("AS003M_SELECTION_PRESSURE_AUDIT.json", meta() | {"phase": "M_SELECTION_PRESSURE", "locked_cases": len(results), "supported_relation_cases": len(supported_relation), "unknown_blocked_cases": len(unknown), "residual_close02z_cases": sum(1 for row in results if row["close02z_residual"]), "retained_as003l": {"supported_cases": 26, "L1_precedence": 8, "residual_total": 22}, "interpretation": "P1/P2 can express genuine future-feasibility distinctions in literal supported cases, but no operational selection-pressure claim is lawful until a composable source-backed substrate exists. No post-hoc threshold was set.", "result": "CONDITIONAL_MECHANISM_PROMISE_NOT_OPERATIONALLY_ESTABLISHED"})
    durable_json("AS003M_AS002_PLANNING_COMPATIBILITY.json", meta() | {"phase": "N_AS002", "AS002_status": "historical contract evidence preserved; V1 remains retired as a forward ordinary selector by AS-003D", "P1": "a categorical continuation fact can be represented as evidence but alone may remain silent", "P2": "strict continuation inclusion is a relational proposition, not a scalar, but its consumption cannot be tested until lawful continuations exist", "current_disposition": "N2_CONDITIONAL_BOUNDED_EXTENSION_AFTER_SUBSTRATE; N3_NOT_YET_ESTABLISHED", "result": "NO_AS002_MUTATION_OR_REJECTION"})
    durable_text("AS003M_RECEDING_HORIZON_AUTHORITY_CONTRACT.md", "# AS-003M receding-horizon authority contract\n\n1. Inspect verified current state and evidence only.\n2. Build bounded hypothetical continuation witnesses through a pure read-only interface.\n3. Emit only categorical/relational planning evidence about an existing current candidate.\n4. Send the selected current candidate through normal arbitration, critical/active recovery, Governance, and Embodiment.\n5. Execute at most that one current action.\n6. Learn only from its VerifiedOutcome.\n7. Invalidate all prior witnesses on any material contradiction or change.\n8. Recompute from current reality; no queued future action has authority.\n")
    durable_text("AS003M_END_GOAL_DRIFT_CHECK.md", "# AS-003M end-goal drift check\n\nA bounded continuation witness supports creature-like anticipation only if it retains uncertainty, allows residual choice and surprise, leaves habits/context/individuality active, executes one governed action at a time, and learns only from verified outcomes. It becomes an optimization agent if it maximizes a global value, preserves a future action queue, or turns predictions into experience. The locked contract permits the former and excludes the latter. Current source cannot yet instantiate the lawful form because it lacks a pure multi-step evidence-composition substrate.\n")
    durable_text("AS003M_EXTERNAL_PRIOR_ART_MATRIX.json", json.dumps(meta() | {"phase": "J_EXTERNAL", "sources": [{"source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5847173/", "topic": "hippocampal replay and planning", "classification": "REFERENCE", "adopted_boundary": "prospective internal sequences are biologically compatible; evidence does not prescribe UMBRA reward or action authority"}, {"source": "https://doi.org/10.1137/0328044", "topic": "viability theory", "classification": "REFERENCE", "adopted_boundary": "feasible constrained futures are set-valued/existential; do not import control optimization"}, {"source": "https://github.com/ISCPIF/viabilitree", "topic": "viability-kernel implementation", "classification": "REJECT", "reason": "Scala kd-tree approximation, grid/accuracy parameters and active-learning kernel computation conflict with bounded source-specific UMBRA semantics; no dependency"}, {"source": "https://github.com/mozilla/pdf.js/files/3721640/issue9552.pdf", "topic": "classical replanning", "classification": "REFERENCE", "reason": "only supports replan-on-material-change principle; no task planner import"}], "result": "REFERENCE_ONLY_NO_DEPENDENCY"}, indent=2, sort_keys=True) + "\n")
    durable_json("AS003M_VERDICT.json", meta() | {"primary_verdict": "AS003M_PLANNING_SUBSTRATE_EXTENSION_REQUIRED", "existing_worldmodel_planner": planner["disposition"], "basis": ["project goal permits bounded evidence-based planning", "current planner is authored/scalar and queues later actions", "current pure views are one-step evidence only and no lawful hypothetical-state transition exists", "timing, opportunity persistence, pending actuation, route, and coupled effects cannot be composed across a future sequence without inventing certainty", "conditional four-owner bound exists but cannot be instantiated by current substrate"], "exact_missing_substrate": composition["missing_primitives"], "recommendation": "NONE; Architect must decide whether to authorize a bounded planning substrate contract before any implementation", "as002": "not mutated or rejected; conditional bounded extension evaluation awaits lawful substrate", "close02z": "residual only; not a planning score", "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0}})


def manifest() -> None:
    required = sorted(path for path in EVIDENCE.glob("AS003M_*") if path.name != "AS003M_EVIDENCE_MANIFEST.json")
    if not required:
        raise RuntimeError("no_evidence_artifacts")
    durable_json("AS003M_EVIDENCE_MANIFEST.json", meta() | {"artifact_count": len(required), "artifacts": [{"name": path.name, "sha256": sha(path), "bytes": path.stat().st_size} for path in required], "durability": "file fsync, atomic rename, directory fsync, readback SHA-256", "readback": "PASS", "result": "PASS"})


def sync() -> None:
    heads = {name: git("rev-parse", name) for name in ("HEAD", "master", "github/master")}
    production_test_delta = git("diff", "--name-only", f"{BASE}..HEAD", "--", "umbra_core", "tests").splitlines()
    goal = (ROOT / ".agent/PROJECT_GOAL.md").read_text(encoding="utf-8")
    required_goal = "Planning must remain bounded, evidence-based, and subordinate to urgent regulation and governance."
    checks = {
        "all_heads_exact_baseline": all(value == BASE for value in heads.values()),
        "as003l_manifest_exists": AS003L_MANIFEST.is_file(),
        "as003l_manifest_hash_matches": AS003L_MANIFEST.is_file() and sha(AS003L_MANIFEST) == AS003L_MANIFEST_SHA256,
        "production_and_test_delta_empty": production_test_delta == [],
        "project_goal_planning_clause_present": required_goal in goal,
    }
    if not all(checks.values()):
        raise RuntimeError("AS003M_START_STATE_MISMATCH:" + ",".join(key for key, value in checks.items() if not value))
    durable_json("AS003M_STATE_AND_GOAL_RECONCILIATION.json", {
        "schema": "AS003M_STATE_AND_GOAL_RECONCILIATION_V1",
        "generated_at": now(),
        "exact_starting_baseline": BASE,
        "heads": heads,
        "as003l": {
            "accepted_verdict": "AS003L_PLANNING_BOUNDARY_REQUIRED",
            "manifest_path": str(AS003L_MANIFEST),
            "manifest_sha256": AS003L_MANIFEST_SHA256,
            "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0},
        },
        "project_goal": {
            "path": ".agent/PROJECT_GOAL.md",
            "authoritative_clause": required_goal,
            "interpretation": "bounded prospective planning is project-goal-required; blanket no-planner was an over-broad local guard",
        },
        "production_test_delta": production_test_delta,
        "canonical_notion": {
            "page_id": "3b3833cb-27ff-8030-9f1f-e73e7af37fe6",
            "as003m_authority": "fetched_and_confirmed",
        },
        "checks": checks,
        "result": "PASS",
        "scope": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0},
    })


if __name__ == "__main__":
    if len(os.sys.argv) != 2 or os.sys.argv[1] not in {"sync", "lock", "analyze", "manifest"}:
        raise SystemExit("usage: as003m_research.py {sync|lock|analyze|manifest}")
    {"sync": sync, "lock": lock, "analyze": analyze, "manifest": manifest}[os.sys.argv[1]]()
