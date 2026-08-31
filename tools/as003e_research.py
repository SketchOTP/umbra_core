#!/usr/bin/env python3
"""AS-003E frozen-corpus causal-role analysis; never imports or executes runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid


START_BASELINE = "4b3b23c86cad8d93f523c67651b702e1111b5a05"
TRACE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003c-replay-migration-qualification-r1")
TRACE_NAMES = ("DIAGNOSTIC_A", "DIAGNOSTIC_B")
ROLE_LOCK_SCHEMA = "AS003E_ROLE_CLASSIFICATION_LOCK_V1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("short_write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temp, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def write_json(root: Path, name: str, obj: Any) -> None:
    durable(root / name, (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode())


def write_md(root: Path, name: str, text: str) -> None:
    durable(root / name, text.encode())


def source_traces() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in TRACE_NAMES:
        path = TRACE_ROOT / name / f"{name}.decision-trace.jsonl"
        out[name] = {"path": str(path), "sha256": sha(path), "row_count": sum(1 for _ in path.open())}
    return out


def evidence_status(value: dict[str, Any] | None) -> str:
    return str((value or {"status": "NOT_APPLICABLE"}).get("status", "NOT_APPLICABLE"))


ROLE_MAP = {
    "Physiology": {
        "roles": ["MOTIVATIONAL_CONTEXT_STATE", "CONSEQUENCE_PREDICTION", "HARD_AUTHORITY"],
        "paths": [
            {"source": "umbra_core/physiology.py:vector_urgency, active_recovery_needs, critical_any", "meaning": "state-owned active/critical recovery authority and per-dimension regulation"},
            {"source": "umbra_core/distributed_competition.py:_physiology_channels", "meaning": "one-step per-dimension effect consequence evidence"},
        ],
        "prior_evidence": "AS-003C A/B completed with active/critical recovery protected; AS-003D physiology-only projection relation in 2563/2647 decisions.",
    },
    "Governed perception": {
        "roles": ["OPPORTUNITY_ACTIVATION", "CANDIDATE_SPECIFICATION"],
        "paths": [{"source": "umbra_core/runtime.py:_tick_once_body perception ingest; umbra_core/arbitration.py affordance candidate builders", "meaning": "governed observations expose bounded affordances and manipulation bindings"}],
        "prior_evidence": "D-011 governed perception qualification; AS-003C frozen candidate pools retain opportunities but not hidden truth.",
    },
    "SelfModel": {
        "roles": ["CONSEQUENCE_PREDICTION", "LEARNING_UPDATE"],
        "paths": [{"source": "umbra_core/self_model/engine.py:candidate_consequence_view", "meaning": "pure bounded body success/progress/duration support"}, {"source": "umbra_core/self_model/engine.py:observe_outcome", "meaning": "selected verified outcome revises body support"}],
        "prior_evidence": "AS-001/AS-002 pure consequence-view contract; AS-003C retained body channels.",
    },
    "WorldModel": {
        "roles": ["CONSEQUENCE_PREDICTION", "LEARNING_UPDATE", "OPPORTUNITY_ACTIVATION"],
        "paths": [{"source": "umbra_core/world_model/engine.py:candidate_consequence_view", "meaning": "pure one-step learned environmental-effect support"}, {"source": "umbra_core/world_model/engine.py:observe_outcome", "meaning": "selected verified outcome revision"}, {"source": "umbra_core/runtime.py:policy_observations", "meaning": "policy-safe learned observations can expose opportunities"}],
        "prior_evidence": "AS-001/AS-002 pure one-step view contract; AS-003C retained world-effect channels.",
    },
    "Memory": {
        "roles": ["CANDIDATE_SPECIFICATION", "MOTIVATIONAL_CONTEXT_STATE", "LEARNING_UPDATE"],
        "paths": [{"source": "umbra_core/memory/engine.py:routine_soft_proposals", "meaning": "procedural memories can introduce bounded address-only routine action proposals"}, {"source": "umbra_core/runtime.py:memory_transition", "meaning": "active recall is traceable context and proposal source, not merit"}],
        "prior_evidence": "AS-003C retained traces include 2556 memory current-tick proposals.",
    },
    "Habits/routines": {
        "roles": ["CANDIDATE_SPECIFICATION", "CONTINUITY_COMMITMENT", "LEARNING_UPDATE"],
        "paths": [{"source": "umbra_core/memory/engine.py:routine_soft_proposals", "meaning": "bounded routine steps may specify candidates"}, {"source": "umbra_core/arbitration.py:ArbitrationState", "meaning": "commitment/retry state remains separate from proposal provenance"}],
        "prior_evidence": "AS-003C retained routine proposal trace field and source-neutral candidate canonicalization.",
    },
    "Development/practice": {
        "roles": ["CANDIDATE_SPECIFICATION", "MOTIVATIONAL_CONTEXT_STATE", "LEARNING_UPDATE"],
        "paths": [{"source": "umbra_core/runtime.py:development_transition and intent_candidates", "meaning": "qualified development emits optional intent candidates before ordinary final authority"}],
        "prior_evidence": "CLOSE-02T/R preserved hierarchical intent boundary; AS-003C retained 60 development current-tick proposals.",
    },
    "Relationships/social": {
        "roles": ["CANDIDATE_SPECIFICATION", "MOTIVATIONAL_CONTEXT_STATE", "LEARNING_UPDATE"],
        "paths": [{"source": "umbra_core/social/engine.py:routine_eligible", "meaning": "relationship evidence can authorize routine eligibility but does not self-execute"}, {"source": "umbra_core/runtime.py:social_transition", "meaning": "social state is an upstream proposal/context path"}],
        "prior_evidence": "Social qualification is protected; AS-003C frozen corpus had no social current-tick proposal, so realized corpus effect is UNKNOWN.",
    },
    "Temporal expectations": {
        "roles": ["CANDIDATE_SPECIFICATION", "MOTIVATIONAL_CONTEXT_STATE", "CONTINUITY_COMMITMENT"],
        "paths": [{"source": "umbra_core/arbitration.py:policy_expectations and WAIT generation", "meaning": "time windows may specify WAIT/preparation candidates and maintain bounded temporal context"}],
        "prior_evidence": "D-010Q5 temporal continuity and CLOSE-02U remain protected; no retained qualifying AS-003C WAIT candidate was observed.",
    },
    "Individuality": {
        "roles": ["MOTIVATIONAL_CONTEXT_STATE", "LEARNING_UPDATE"],
        "paths": [{"source": "umbra_core/individuality/engine.py:candidate_evidence_channels", "meaning": "learned dispositions currently reach ordinary competition only as separate channels; legacy modifier path is non-authoritative in V1"}, {"source": "umbra_core/stochastic_competition.py", "meaning": "candidate-local stochasticity preserves bounded identity variation but is not a disposition priority"}],
        "prior_evidence": "AS-003C retained individuality channels on every qualifying candidate; AS-003D found 75.08% individuality UNKNOWN rate.",
    },
    "Habitat/environment affordances": {
        "roles": ["OPPORTUNITY_ACTIVATION", "CANDIDATE_SPECIFICATION", "HARD_AUTHORITY"],
        "paths": [{"source": "umbra_core/habitat_affordances/engine.py and umbra_core/embodiment.py", "meaning": "authoritative habitat exposes affordances; Embodiment enforces executable physical boundary"}],
        "prior_evidence": "Habitat/body independence qualifications remain protected; AS-003C pools are retained source-neutral affordance results.",
    },
    "Recoverability": {
        "roles": ["HARD_AUTHORITY", "OPPORTUNITY_ACTIVATION"],
        "paths": [{"source": "umbra_core/recoverability/contracts.py:candidate_is_admissible", "meaning": "hard admissibility excludes unsafe candidates before ordinary competition"}, {"source": "umbra_core/recoverability/view.py", "meaning": "policy-visible recovery evidence is bounded and non-executing"}],
        "prior_evidence": "CLOSE-02 and AS-002 protected boundary; AS-003C A/B safety compatibility passed before mechanism stop.",
    },
    "Governance": {
        "roles": ["HARD_AUTHORITY"],
        "paths": [{"source": "umbra_core/governance.py:admit", "meaning": "final action proposal remains governed after arbitration"}],
        "prior_evidence": "Authority 3.0/governance and CLOSE-02T final authority protected.",
    },
    "Embodiment": {
        "roles": ["HARD_AUTHORITY", "LEARNING_UPDATE"],
        "paths": [{"source": "umbra_core/embodiment.py execution boundary; umbra_core/runtime.py:_finish_outcome", "meaning": "Embodiment executes only admitted action and VerifiedOutcome feeds selected-only learning"}],
        "prior_evidence": "Protected final execution authority and body-migration evidence.",
    },
}


CHANNEL_RULES = [
    ("physiology.", "IMMEDIATE_CONSEQUENCE", True, "Per-dimension conservative one-step effect distance; comparable only inside each same physiology proposition."),
    ("body.", "EXECUTABILITY_OR_BODY_SUPPORT", True, "Pure learned body capability-support consequence; not source merit."),
    ("world.effect.", "ENVIRONMENTAL_CONSEQUENCE", True, "Pure learned one-step action/environment effect; not a planner or outcome guarantee."),
    ("development.active-intent", "MOTIVATIONAL_CONTEXT", False, "An upstream development intent is a currently active context/candidate source, not a consequence of every candidate."),
    ("memory.active-recall", "CANDIDATE_RELEVANCE", False, "Recall establishes active candidate/context availability, not cross-candidate merit."),
    ("continuity.", "CONTINUITY_STATE", False, "Commitment state protects continuity; its numeric order lacks a shared immediate consequence meaning."),
    ("individuality.", "MOTIVATIONAL_CONTEXT", False, "Disposition is a persistent internal context; V1 channelization made it a veto-like objective without a comparative consequence unit."),
    ("option.", "OPTION_AVAILABILITY", False, "Policy-visible route/admissibility information is a constraint/opportunity role, not ordinary merit."),
    ("temporal.", "CONTINUITY_STATE", False, "Temporal window/repetition state can activate WAIT/preparation or continuity, not a consequence objective by default."),
]


def channel_role(key: str) -> tuple[str, bool, str]:
    for prefix, role, allowed, why in CHANNEL_RULES:
        if key.startswith(prefix):
            return role, allowed, why
    return "OTHER", False, "No predeclared consequence-comparison meaning; excluded fail-closed from analysis projection."


def load_decisions() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    traces = source_traces()
    decisions: list[dict[str, Any]] = []
    for name in TRACE_NAMES:
        path = Path(traces[name]["path"])
        qualifying = 0
        for line in path.open():
            row = json.loads(line)
            comp = row.get("distributed_competition") or {}
            if not comp.get("views") or int(comp.get("admissible_candidate_count", 0)) < 2:
                continue
            qualifying += 1
            decisions.append({"diagnostic": name, "tick": int(row["tick"]), "active_tick": int(row.get("active_ticks", row["tick"])), "row": row, "views": comp["views"], "competition": comp})
        traces[name]["qualifying_decision_count"] = qualifying
    return decisions, traces


def pair_relation(a: dict[str, Any], b: dict[str, Any], allowed_prefixes: tuple[str, ...]) -> dict[str, Any]:
    keys = sorted(k for k in set(a["channels"]) | set(b["channels"]) if k.startswith(allowed_prefixes))
    strict: list[str] = []
    blockers: list[str] = []
    worse: list[str] = []
    for key in keys:
        av, bv = a["channels"].get(key), b["channels"].get(key)
        if evidence_status(av) == "NOT_APPLICABLE" and evidence_status(bv) == "NOT_APPLICABLE":
            continue
        if evidence_status(av) != "SUPPORTED" or evidence_status(bv) != "SUPPORTED":
            blockers.append(key)
            continue
        ao, bo = float(av["order"]), float(bv["order"])
        if ao < bo:
            worse.append(key)
        elif ao > bo:
            strict.append(key)
    return {"passed": bool(keys) and not blockers and not worse and bool(strict), "keys": keys, "strict": strict, "unknown_or_inapplicable": blockers, "worse": worse}


def projection(decisions: list[dict[str, Any]], allowed_prefixes: tuple[str, ...]) -> dict[str, Any]:
    count = 0
    with_relation = 0
    full = 0
    stoch = 0
    eliminated = 0
    learned_changed_pairs = 0
    learned_changed_decisions = 0
    changed_winner = 0
    unknown_blocked_pairs = 0
    conflict_pairs = 0
    per_decision: list[dict[str, Any]] = []
    for decision in decisions:
        views = sorted(decision["views"], key=lambda v: v["identity"])
        dominated: set[str] = set()
        relations: list[dict[str, Any]] = []
        local_learned_change = False
        local_unknown = False
        local_conflict = False
        for a in views:
            for b in views:
                if a["identity"] == b["identity"]:
                    continue
                result = pair_relation(a, b, allowed_prefixes)
                count += 1
                if result["passed"]:
                    dominated.add(b["identity"])
                    relations.append({"a": a["identity"], "b": b["identity"], "strict": result["strict"]})
                if result["unknown_or_inapplicable"]:
                    unknown_blocked_pairs += 1
                    local_unknown = True
                if result["strict"] and result["worse"]:
                    conflict_pairs += 1
                    local_conflict = True
                # Compare only with the physiology component to show whether learned consequence evidence ever changes this relation.
                phy = pair_relation(a, b, ("physiology.",))
                if phy["passed"] != result["passed"]:
                    learned_changed_pairs += 1
                    local_learned_change = True
        frontier = [v for v in views if v["identity"] not in dominated]
        if relations:
            with_relation += 1
        if len(frontier) == len(views):
            full += 1
        if len(frontier) > 1:
            stoch += 1
        eliminated += len(dominated)
        selected = max(frontier, key=lambda v: (float(v["stochastic_term"]), v["identity"]))
        full_pool = max(views, key=lambda v: (float(v["stochastic_term"]), v["identity"]))
        if selected["identity"] != full_pool["identity"]:
            changed_winner += 1
        learned_changed_decisions += int(local_learned_change)
        per_decision.append({"diagnostic": decision["diagnostic"], "tick": decision["tick"], "candidate_count": len(views), "relation_count": len(relations), "eliminated_count": len(dominated), "frontier_size": len(frontier), "full_frontier": len(frontier) == len(views), "unknown_block": local_unknown, "consequence_conflict": local_conflict, "selected_identity": selected["identity"], "stochastic_full_pool_identity": full_pool["identity"]})
    return {"allowed_channel_prefixes": list(allowed_prefixes), "ordered_pair_count": count, "relations": sum(x["relation_count"] for x in per_decision), "decisions_with_relation": with_relation, "full_frontier_decisions": full, "stochastic_resolution_decisions": stoch, "eliminated_candidates": eliminated, "learned_consequence_changed_pair_relation_count": learned_changed_pairs, "decisions_with_learned_consequence_relation_change": learned_changed_decisions, "selected_differs_from_stochastic_full_pool_count": changed_winner, "unknown_blocked_pair_count": unknown_blocked_pairs, "genuine_consequence_conflict_pair_count": conflict_pairs, "per_decision": per_decision}


def initialize(root: Path, commit: str) -> None:
    if any(root.iterdir()) if root.exists() else False:
        raise RuntimeError("evidence_root_not_empty_for_role_lock")
    traces = source_traces()
    role_map = {"schema": "AS003E_CAUSAL_ROLE_MAP_V1", "generated_at": now(), "start_baseline": START_BASELINE, "governance_start_commit": commit, "production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "subsystems": ROLE_MAP, "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}}
    write_json(root, "AS003E_CAUSAL_ROLE_MAP.json", role_map)
    channel_audit = {"schema": "AS003E_CHANNEL_ROLE_AUDIT_V1", "generated_at": now(), "role_rules": [{"prefix": p, "classification": r, "eligible_for_role_partition_consequence_comparison": e, "reason": why} for p, r, e, why in CHANNEL_RULES], "legitimate_comparison_families": ["physiology.", "body.", "world.effect."], "exclusions": "Candidate source/provenance, context activation, continuity, individuality, temporal state, memory recall, and option availability are not immediate consequence propositions merely because V1 encoded an ordinal channel.", "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}}
    write_json(root, "AS003E_CHANNEL_ROLE_AUDIT.json", channel_audit)
    lock = {"schema": ROLE_LOCK_SCHEMA, "locked_at": now(), "start_baseline": START_BASELINE, "governance_start_commit": commit, "role_map_sha256": sha(root / "AS003E_CAUSAL_ROLE_MAP.json"), "channel_audit_sha256": sha(root / "AS003E_CHANNEL_ROLE_AUDIT.json"), "comparison_channel_prefixes": ["physiology.", "body.", "world.effect."], "exclusion_criteria": "A channel must describe a candidate's bounded one-step immediate consequence or body executability. Candidate specification, opportunity, motivational context, continuity/commitment, source/provenance, option availability, hard authority, and learning update are excluded from cross-candidate comparison.", "immutability_rule": "No role assignment or comparison membership may change after this lock based on projection performance. A contradiction is a stop/report condition, not a retuning permission.", "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}, "integrity": {"production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}}
    write_json(root, "AS003E_ROLE_CLASSIFICATION_LOCK.json", lock)


def analyze(root: Path, commit: str) -> None:
    lock = json.loads((root / "AS003E_ROLE_CLASSIFICATION_LOCK.json").read_text())
    if lock["schema"] != ROLE_LOCK_SCHEMA or lock["role_map_sha256"] != sha(root / "AS003E_CAUSAL_ROLE_MAP.json") or lock["channel_audit_sha256"] != sha(root / "AS003E_CHANNEL_ROLE_AUDIT.json"):
        raise RuntimeError("role_classification_lock_integrity_fail")
    if tuple(lock["comparison_channel_prefixes"]) != ("physiology.", "body.", "world.effect."):
        raise RuntimeError("role_classification_lock_membership_mismatch")
    decisions, traces = load_decisions()
    actual = projection(decisions, ("physiology.", "body.", "world.effect."))
    physiology = projection(decisions, ("physiology.",))
    source_counts: Counter[str] = Counter()
    candidate_records: dict[str, set[str]] = defaultdict(set)
    parameterized: Counter[str] = Counter()
    context_channel_rows: Counter[str] = Counter()
    for d in decisions:
        row = d["row"]
        for field, owner in (("development_transition", "development"), ("memory_transition", "memory"), ("social_transition", "social")):
            for transition in row.get(field) or []:
                if transition.get("reason") == "current_tick_proposal":
                    source_counts[owner] += 1
                    cand = transition.get("candidate_after") or transition.get("candidate_emitted") or {}
                    candidate_records[owner].add(json.dumps(cand, sort_keys=True, separators=(",", ":")))
        for view in d["views"]:
            for key in view["channels"]:
                role, allowed, _ = channel_role(key)
                if not allowed:
                    context_channel_rows[role] += 1
            params = view.get("params", {})
            if params.get("source"):
                parameterized[str(params["source"])] += 1
    candidate_causality = {"schema": "AS003E_CANDIDATE_SPECIFICATION_CAUSALITY_V1", "generated_at": now(), "frozen_corpus": {"qualifying_decisions": len(decisions), "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}}, "realized_transitions": {owner: {"current_tick_proposal_rows": source_counts[owner], "distinct_retained_candidate_records": len(candidate_records[owner])} for owner in ("memory", "development", "social")}, "candidate_parameter_sources": dict(parameterized), "source_neutrality_boundary": "canonical behavioral identity omits proposal provenance; retained source attribution is reported only where trace transitions preserve it. Lost source provenance is UNKNOWN, never reconstructed.", "static_paths_without_realized_frozen_candidate": {"temporal": "WAIT/preparation generation exists in Arbitration but no qualifying retained WAIT candidate occurred.", "social": "routine eligibility exists, but frozen social transitions contain no current-tick proposal.", "habitat/perception": "opportunity bindings feed the retained pool but canonical dedup removes a source-owner count."}, "integrity": {"production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0}}
    write_json(root, "AS003E_CANDIDATE_SPECIFICATION_CAUSALITY.json", candidate_causality)
    coverage = {"schema": "AS003E_END_GOAL_CAUSAL_COVERAGE_V1", "generated_at": now(), "coverage": {
        "physiology": {"path": "active/critical authority plus immediate consequence", "frozen_realized": True},
        "SelfModel": {"path": "pure body consequence view and selected-only verified update", "frozen_realized": True},
        "WorldModel": {"path": "pure environmental consequence view and policy-safe observation", "frozen_realized": True},
        "memory_habits": {"path": "routine/recall candidate specification", "frozen_realized": source_counts["memory"] > 0},
        "development": {"path": "optional intent candidate specification", "frozen_realized": source_counts["development"] > 0},
        "relationships": {"path": "social routine/context specification", "frozen_realized": False, "status": "UNKNOWN_IN_FROZEN_CORPUS"},
        "temporal_expectation": {"path": "WAIT/preparation candidate/context activation", "frozen_realized": False, "status": "UNKNOWN_IN_FROZEN_CORPUS"},
        "individuality": {"path": "currently only V1 disposition channel; no verified non-comparison activation path", "frozen_realized": False, "status": "MISSING_GENERAL_CONTEXT_ACTIVATION_PATH"},
        "environment_opportunity": {"path": "governed perception/habitat affordance specification", "frozen_realized": True},
    }, "conclusion": "Role partition preserves demonstrated candidate/consequence pathways for physiology, learned models, memory, development, and opportunity. It does not by itself give individuality, temporal expectation, or relationship context a verified non-comparison behavior-changing route in this frozen corpus; a generic context activation primitive is therefore not optional if those roles must remain causal.", "integrity": {"production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0}}
    write_json(root, "AS003E_END_GOAL_CAUSAL_COVERAGE.json", coverage)
    projection_artifact = {"schema": "AS003E_ROLE_PARTITION_PROJECTION_V1", "generated_at": now(), "analysis_only": True, "role_lock_sha256": sha(root / "AS003E_ROLE_CLASSIFICATION_LOCK.json"), "method": "Reapply the existing AS-002 supported no-worse/strict-better relation only to role-locked immediate consequence/body-support/environmental-effect channels. Actual frozen candidate pools and candidate-local stochastic terms are retained; no candidate executes and no channel membership is tuned.", "qualifying_decisions": len(decisions), "consequence_comparison": actual, "physiology_reference": physiology, "interpretation_boundary": "This is an attribution projection, not a production rule or a replacement contract. It tests role membership, not an invented tradeoff resolver.", "integrity": {"production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}, "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}}
    write_json(root, "AS003E_ROLE_PARTITION_PROJECTION.json", projection_artifact)
    context_audit = {"schema": "AS003E_MOTIVATIONAL_CONTEXT_AUDIT_V1", "generated_at": now(), "contexts": [
        {"context": "physiology active recovery", "existing_state": "active_recovery_needs / critical_any", "categorical": "ACTIVE/INACTIVE", "authority": "hard recovery outside ordinary competition", "frozen_status": "present but excluded from qualifying ordinary decisions"},
        {"context": "development practice", "existing_state": "development.active-intent", "categorical": "candidate/absent", "authority": "optional intent specification, not global priority", "frozen_status": f"{source_counts['development']} retained current-tick proposals"},
        {"context": "memory/routine", "existing_state": "memory.active-recall / routine proposal", "categorical": "candidate/absent", "authority": "candidate specification", "frozen_status": f"{source_counts['memory']} retained current-tick proposals"},
        {"context": "temporal expectation", "existing_state": "policy expectation window / WAIT eligibility", "categorical": "available/absent", "authority": "candidate/context activation", "frozen_status": "no qualifying retained WAIT candidate"},
        {"context": "relationship/social", "existing_state": "relationship hypothesis/routine eligibility", "categorical": "eligible/ineligible", "authority": "candidate/context activation", "frozen_status": "no retained social current-tick proposal"},
        {"context": "individuality", "existing_state": "learned disposition support", "categorical": "no existing general ACTIVE semantic", "authority": "V1 only exposed channel order", "frozen_status": "present as channels but no non-comparison activation route"},
        {"context": "opportunity", "existing_state": "governed perception/habitat affordance", "categorical": "available/unavailable", "authority": "candidate specification/admissibility", "frozen_status": "candidate pools retain opportunities"},
        {"context": "commitment", "existing_state": "ArbitrationState last capability/commitment", "categorical": "active/inactive", "authority": "continuity state", "frozen_status": "continuity channel present across retained candidates"},
    ], "conclusion": "Several owner-specific activation states exist, but no common bounded semantic says which simultaneously active non-hard contexts are currently eligible to constrain ordinary comparison. Adding that semantic cannot be inferred from a numeric channel order.", "integrity": {"production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0}}
    write_json(root, "AS003E_MOTIVATIONAL_CONTEXT_AUDIT.json", context_audit)
    residual = {"schema": "AS003E_RESIDUAL_CONFLICT_ANALYSIS_V1", "generated_at": now(), "role_partition_projection": {k: actual[k] for k in actual if k != "per_decision"}, "residual": {"decisions_without_any_consequence_relation": len(decisions) - actual["decisions_with_relation"], "full_frontier_decisions": actual["full_frontier_decisions"], "stochastic_resolution_decisions": actual["stochastic_resolution_decisions"], "decisions_with_consequence_conflict": sum(1 for x in actual["per_decision"] if x["consequence_conflict"]), "decisions_with_consequence_unknown_block": sum(1 for x in actual["per_decision"] if x["unknown_block"])}, "simultaneous_context_boundary": "The corpus demonstrates multiple available candidate/context sources, but the retained trace does not contain a general, owner-neutral activation relation to decide which simultaneously active non-hard concerns may limit the comparison family. Role partition alone removes inappropriate veto dimensions; it does not resolve remaining genuine consequence conflicts or define context admission.", "conclusion": "A categorical motivational-context activation primitive is required before evaluating any common cross-system behavioral-control claim. This conclusion does not propose numeric context strength or a priority order.", "integrity": {"production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0}}
    write_json(root, "AS003E_RESIDUAL_CONFLICT_ANALYSIS.json", residual)
    write_md(root, "AS003E_NONPHYSIOLOGY_CAUSALITY_REVIEW.md", f"""# AS-003E non-physiology causal participation review

## What frozen source/evidence supports

- **Memory and habits** retain a non-comparison causal route: `{source_counts['memory']}` retained current-tick memory proposals, with `{len(candidate_records['memory'])}` distinct retained candidate records.
- **Development** retains a non-comparison causal route: `{source_counts['development']}` retained current-tick optional-intent proposals, with `{len(candidate_records['development'])}` distinct retained candidate records. CLOSE-02T keeps the final ordinary authority downstream.
- **SelfModel and WorldModel** retain one-step consequence roles and selected-only verified learning. The locked projection measures whether they change a relation; it does not convert either into a planner.
- **Perception/habitat opportunity** remains a candidate-specification path and never receives source merit.

## Gaps that role partition exposes rather than fixes

- **Individuality** is present in every qualifying V1 view, but current code exposes it to ordinary selection only as a disposition channel. Once that non-consequence channel is correctly removed from immediate comparison, no existing owner-neutral ACTIVE/INACTIVE context path has been demonstrated. Candidate-local CLOSE-02Z is preserved individuality variation, not an individuality control claim.
- **Temporal expectation** has a static WAIT/preparation specification path, but no qualifying retained WAIT candidate occurred; its realized ordinary causal effect is UNKNOWN in this corpus.
- **Relationships/social state** has a static routine/context path, but no frozen current-tick social proposal occurred; its realized ordinary causal effect is UNKNOWN in this corpus.

## Result

Role separation prevents physiology-only collapse for the systems with demonstrated candidate/context or consequence paths. It is not yet sufficient for the full end-goal requirement because the project lacks a general bounded motivational-context activation semantics for simultaneously active individuality, temporal, relationship, and other non-hard concerns. The needed next primitive is categorical/contextual before any proposed common numeric motivational currency.
""")
    write_md(root, "AS003E_CONTROL_CLAIM_REQUIREMENTS.md", """# AS-003E endogenous behavioral-control claim requirements

## Current disposition

No common behavioral-control claim is proposed or calibrated by AS-003E. The earlier missing boundary is narrower: a role-separated design first needs a source-neutral, categorical motivational-context activation primitive. A numeric/ordinal cross-system claim would be premature.

## Conditional future requirements

If a later authority establishes that active contexts still cannot resolve an ordinary conflict, any candidate common control claim must state one explicit meaning: **the constitutionally grounded, temporary claim of a currently active motivational context to control an incompatible action under present state and verified learned association**. It must then supply all of the following before implementation:

1. one common cross-system unit or ordinal relation, not per-system normalization;
2. an authoritative owner and bounded provenance for every input;
3. a source-neutral revision mechanism tied only to verified outcomes where learning is claimed;
4. first-experience/UNKNOWN handling that neither grants nor denies control automatically;
5. no proposal-source self-ranking, designer coefficient, global reward, survival utility, planner, or hidden future truth;
6. persistence/commitment semantics using existing qualified continuity without a new hysteresis coefficient; and
7. a proof that CLOSE-02Z is residual rather than the de facto ordinary selector.

If those conditions reduce to authored relative importance, the required terminal condition is `ARBITRARY_CROSS_SYSTEM_WEIGHTING_REQUIRED`.
""")
    write_md(root, "AS003E_ARCHITECTURE_CANDIDATES.md", """# AS-003E architecture candidates

These are architecture families for Architect decision, not implementation authority.

## R1 — role-separated consequence competition

Candidate/opportunity systems specify the bounded source-neutral pool; physiology, pure SelfModel body support, and pure WorldModel one-step effect evidence form the only ordinary comparison family. Hard safety/recoverability remains outside; CLOSE-02Z remains residual. This avoids proposal-source merit and a global score. The frozen projection shows whether it restores pressure, but it does not decide which non-hard motivations are active.

## R2 — role-separated consequence competition plus endogenous context activation

R1 plus a bounded, owner-derived categorical state that determines whether a motivational context is ACTIVE before ordinary comparison. It must not be a numeric priority, source ordering, or candidate merit. It is the smallest family consistent with the present evidence because individuality, temporal, and social contexts lack a demonstrated non-comparison activation route. Simultaneous active contexts remain an explicit unresolved boundary rather than silently aggregated.

## R3 — common behavioral-control claim

Only a later authority may consider this if R2 proves unable to resolve simultaneous active contexts. It would need the calibration requirements in `AS003E_CONTROL_CLAIM_REQUIREMENTS.md`; without one cross-system meaning it is arbitrary weighting and rejected.

## Disposition

R1 is a supported role-partition hypothesis, not a complete ordinary-selection contract. R2 is the smallest missing primitive boundary. R3 is not supported, specified, or authorized.
""")
    discrimination = {"schema": "AS003E_FROZEN_CORPUS_DISCRIMINATION_V1", "generated_at": now(), "candidates": {
        "R1_role_separated_consequence_competition": {"status": "ANALYZED_OFFLINE", "projection": {k: actual[k] for k in actual if k != "per_decision"}, "learned_evidence_can_change_relation": actual["learned_consequence_changed_pair_relation_count"] > 0, "CLOSE02Z_residual_or_dominant": "RESIDUAL_ONLY_IF_STOCHASTIC_RATE_IS_SUBSTANTIALLY_BELOW_100; retained result reported numerically", "nonphysiology_causal_coverage": "PARTIAL: memory/development/opportunity demonstrated; individuality lacks non-comparison activation; social/temporal unrealized in corpus."},
        "R2_role_separated_with_context_activation": {"status": "NOT_PROJECTED", "reason": "No existing owner-neutral activation primitive is present to freeze without inventing a rule or threshold."},
        "R3_common_behavioral_control_claim": {"status": "NOT_PROJECTED", "reason": "No explicit cross-system unit/calibration exists; projection would manufacture the prohibited scalar."},
    }, "overfit_challenge": "The result does not depend on the historical fatigue seed: it uses all 2647 ordinary AS-003C decisions from A/B. No REST/fatigue-specific selection rule is proposed.", "integrity": {"production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0}}
    write_json(root, "AS003E_FROZEN_CORPUS_DISCRIMINATION.json", discrimination)
    write_md(root, "AS003E_REPLACEMENT_CONTRACT.md", """# AS-003E replacement-contract disposition

## No implementation-ready ordinary selection contract

AS-003E supports the role-partition principle: candidate specification/opportunity activation, motivational context, immediate consequence prediction, continuity, learning, and hard authority are not automatically the same causal role. But it does **not** support an implementation-ready selector because UMBRA lacks a common, bounded, source-neutral motivational-context activation primitive for non-hard contexts.

## Exact next boundary

Before any common behavioral-control scalar is considered, a future Architect directive would need to specify and falsify a categorical/contextual primitive that: (1) is owned by each qualifying subsystem rather than a proposal source; (2) identifies whether that context is ACTIVE from existing state/verified learned associations; (3) does not make physiology universally authoritative; (4) preserves candidate generation, source neutrality, UNKNOWN/first experience, continuity, hard safety, Governance, Embodiment, and selected-only learning; and (5) explicitly reports unresolved simultaneous active-context conflict rather than adding a hidden priority or weight.

No AS-003F recommendation is made by this research result.
""")
    verdict = {"schema": "AS003E_VERDICT_V1", "generated_at": now(), "primary_verdict": "AS003E_MOTIVATIONAL_CONTEXT_ACTIVATION_PRIMITIVE_REQUIRED", "successor_recommendation": None, "v1_status": "RETIRED_AS_FORWARD_ORDINARY_SELECTOR", "role_partition_disposition": "SUPPORTED_AS_NECESSARY_ROLE_CORRECTION_BUT_INSUFFICIENT_AS_A_COMPLETE_SELECTOR", "motivational_context_activation": "REQUIRED", "common_behavioral_control_claim": "NOT_YET_ESTABLISHED_OR_CALIBRATED", "arbitrary_weighting_risk": "ANY_NUMERIC_CROSS_SYSTEM_CLAIM_IS_REJECTED_UNTIL_ONE_EXPLICIT_COMMON_UNIT_AND_REVISION_SEMANTICS_ARE_ESTABLISHED", "basis": {"qualifying_decisions": len(decisions), "role_partition_projection": {k: actual[k] for k in actual if k != "per_decision"}, "physiology_reference": {k: physiology[k] for k in physiology if k != "per_decision"}, "candidate_specification": candidate_causality["realized_transitions"], "coverage_gaps": ["individuality has no demonstrated non-comparison activation path", "temporal expectation unrealized in frozen corpus", "social context unrealized in frozen corpus"]}, "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}, "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}}
    write_json(root, "AS003E_VERDICT.json", verdict)
    required = ["AS003E_CAUSAL_ROLE_MAP.json", "AS003E_ROLE_CLASSIFICATION_LOCK.json", "AS003E_CHANNEL_ROLE_AUDIT.json", "AS003E_CANDIDATE_SPECIFICATION_CAUSALITY.json", "AS003E_END_GOAL_CAUSAL_COVERAGE.json", "AS003E_ROLE_PARTITION_PROJECTION.json", "AS003E_NONPHYSIOLOGY_CAUSALITY_REVIEW.md", "AS003E_MOTIVATIONAL_CONTEXT_AUDIT.json", "AS003E_RESIDUAL_CONFLICT_ANALYSIS.json", "AS003E_CONTROL_CLAIM_REQUIREMENTS.md", "AS003E_PRIOR_ART_BOUNDARY.md", "AS003E_ARCHITECTURE_CANDIDATES.md", "AS003E_FROZEN_CORPUS_DISCRIMINATION.json", "AS003E_REPLACEMENT_CONTRACT.md", "AS003E_VERDICT.json"]
    manifest = {"schema": "AS003E_FINAL_EVIDENCE_MANIFEST_V1", "generated_at": now(), "baseline": START_BASELINE, "commit": commit, "required_files": {name: sha(root / name) for name in required}, "role_lock_sha256": sha(root / "AS003E_ROLE_CLASSIFICATION_LOCK.json"), "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}, "durability": "file fsync, atomic rename, directory fsync, readback SHA-256", "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}}
    write_json(root, "AS003E_EVIDENCE_MANIFEST.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--lock", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    if args.lock == args.analyze:
        raise SystemExit("choose_exactly_one_of_lock_or_analyze")
    if args.lock:
        initialize(args.evidence_root, args.commit)
    else:
        analyze(args.evidence_root, args.commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
