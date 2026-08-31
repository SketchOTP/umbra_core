#!/usr/bin/env python3
"""AS-003F static/frozen-corpus research; never imports or executes UMBRA runtime."""
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


ARCHITECT_BASELINE = "7381af06a5a7b8b15e751f296cde18feec315585"
TRACE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003c-replay-migration-qualification-r1")
TRACE_NAMES = ("DIAGNOSTIC_A", "DIAGNOSTIC_B")
LOCK_SCHEMA = "AS003F_CONTEXT_ACTIVATION_AND_RESOLUTION_LOCK_V1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        offset = 0
        while offset < len(data):
            count = os.write(fd, data[offset:])
            if count <= 0:
                raise OSError("short_write")
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def write_json(root: Path, name: str, value: Any) -> None:
    durable(root / name, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def write_md(root: Path, name: str, value: str) -> None:
    durable(root / name, value.encode())


def source_traces() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in TRACE_NAMES:
        path = TRACE_ROOT / name / f"{name}.decision-trace.jsonl"
        result[name] = {"path": str(path), "sha256": sha(path), "row_count": sum(1 for _ in path.open())}
    return result


# This lock intentionally describes activation *meaning*, not a formula or a
# proposed production implementation. UNKNOWN is an evidence state, not an
# activation rank; it cannot self-promote and cannot block first experience.
OWNER_INVENTORY = {
    "physiology": {
        "owner": "Physiology",
        "evidence_inputs": ["viable/critical bands", "active_recovery_needs", "per-dimension state"],
        "candidate_implications": "Existing recovery/preventive candidate generation; hard recovery stays outside this contract.",
        "satisfaction_deactivation": "authoritative state returns outside the owner-defined active band; verified outcome may update only downstream learned models, not physiology itself",
        "existing_persistence": "physiology state persists; non-hard categorical activation is not currently exposed",
        "learning": "none for constitutional physiology state; selected-only learning remains in SelfModel/WorldModel",
    },
    "temporal_expectation": {
        "owner": "TemporalEngine",
        "evidence_inputs": ["PolicyExpectationView status", "expectation version", "open/preparation window"],
        "candidate_implications": "WAIT/preparation candidate specification when current policy semantics allow it.",
        "satisfaction_deactivation": "window completes/passes, expectation status changes, or authoritative recurrence revision",
        "existing_persistence": "versioned temporal state persists across restart/migration",
        "learning": "recurrence revision is owner-local; no update from an unexecuted candidate",
    },
    "habit_routine": {
        "owner": "MemoryEngine procedural memory",
        "evidence_inputs": ["bounded procedural routine", "eligibility", "policy-visible bindings/current step"],
        "candidate_implications": "bounded MANIPULATE/routine proposals; provenance remains non-authoritative",
        "satisfaction_deactivation": "owner-established procedure completion, invalid binding, or verified outcome/denial",
        "existing_persistence": "procedural state and bounded routine lifecycle persist",
        "learning": "only selected verified outcomes revise memory",
    },
    "development_practice": {
        "owner": "DevelopmentEngine",
        "evidence_inputs": ["selected practice goal", "readiness/risk/resource constraints", "current goal-to-capability mapping"],
        "candidate_implications": "optional practice intent candidate; final ordinary action authority remains downstream",
        "satisfaction_deactivation": "owner goal completion, invalidity, readiness loss, or verified outcome revision",
        "existing_persistence": "goals and active goal state persist",
        "learning": "competence/goal state changes only through selected verified outcome",
    },
    "relationship_social": {
        "owner": "SocialEngine",
        "evidence_inputs": ["partner/context state", "policy-visible social cues", "routine eligibility"],
        "candidate_implications": "social proposal/context may specify an existing candidate; no self-execution",
        "satisfaction_deactivation": "partner/opportunity disappearance, owner context change, verified completion/denial",
        "existing_persistence": "relationship hypotheses and routine handles persist",
        "learning": "selected verified social outcome only",
    },
    "memory_recall": {
        "owner": "MemoryEngine",
        "evidence_inputs": ["active recalled item", "policy-visible retrieved association", "bounded proposal relation"],
        "candidate_implications": "may specify bounded action candidates; recall provenance is never merit",
        "satisfaction_deactivation": "recall no longer active, item invalidated/forgotten, or owner changes working state",
        "existing_persistence": "bounded memory/working state persists",
        "learning": "selected verified outcomes only",
    },
    "environment_opportunity": {
        "owner": "governed perception / habitat authority",
        "evidence_inputs": ["policy-visible affordance/cue", "Embodiment executability", "recoverability admissibility"],
        "candidate_implications": "enables or parameterizes existing candidates; opportunity alone is not motivation",
        "satisfaction_deactivation": "cue/affordance disappears or becomes inadmissible",
        "existing_persistence": "environmental state belongs to habitat, not a new motivation cache",
        "learning": "WorldModel changes only from selected verified outcomes",
    },
    "engaged_behavioral_context": {
        "owner": "new shared context state would be required; existing ArbitrationState only records action continuity",
        "evidence_inputs": ["previously selected context identity plus owner revalidation"],
        "candidate_implications": "would bound the relevant candidate subset after a valid engagement decision",
        "satisfaction_deactivation": "must derive from owner deactivation/completion/verified blockage or hard interruption",
        "existing_persistence": "existing capability continuity is not a source-neutral context engagement identity",
        "learning": "no counterfactual learning; selected verified outcomes only",
    },
    "individuality": {
        "owner": "IndividualityEngine",
        "evidence_inputs": ["persistent disposition estimate and context scope"],
        "candidate_implications": "V1 channelization was retired; no verified non-comparison activation path exists",
        "satisfaction_deactivation": "no owner-neutral active/inactive lifecycle currently established",
        "existing_persistence": "disposition ledger persists",
        "learning": "selected verified outcomes update the ledger",
    },
}


ACTIVATION_AUDIT = {
    "physiology": {"status": "CONTEXT_SUBSTRATE_PARTIAL", "activation": "Hard active/critical recovery is already categorical hard authority. Non-hard preventive relevance is currently represented through owner-local magnitude, not an established categorical active context.", "risk": "Do not convert vector_urgency numeric values into an unqualified activation threshold."},
    "temporal_expectation": {"status": "OWNER_CATEGORICAL_EVIDENCE_AVAILABLE", "activation": "An ACTIVE policy expectation with its existing open/preparation semantics may establish temporal relevance; UNCERTAIN is evidence-quality, not a self-promoting active claim.", "risk": "No claim is made for a retained A/B realization."},
    "habit_routine": {"status": "OWNER_CATEGORICAL_EVIDENCE_PARTIAL", "activation": "A current eligible routine with valid binding can establish routine relevance; mere historical memory cannot.", "risk": "proposal presence alone must not become merit."},
    "development_practice": {"status": "OWNER_CATEGORICAL_EVIDENCE_AVAILABLE", "activation": "A selected, currently valid practice goal that emits a candidate can establish a development context; its internal selection is not exported as cross-owner strength.", "risk": "risk/readiness numerics cannot become common priority."},
    "relationship_social": {"status": "OWNER_CATEGORICAL_EVIDENCE_PARTIAL", "activation": "Current partner/context state plus a policy-visible matching cue/proposal can establish social relevance.", "risk": "no affection score and no retained realized A/B social proposal."},
    "memory_recall": {"status": "CONTEXT_SUBSTRATE_PARTIAL", "activation": "A bounded currently recalled relation can make a candidate relevant, but existing evidence does not establish recall itself as a motivational owner.", "risk": "recalled salience is not automatically motivation."},
    "environment_opportunity": {"status": "NOT_A_MOTIVATIONAL_OWNER", "activation": "Opportunity enables/parameterizes actions for an owner context; it does not independently establish that a concern is active.", "risk": "must not self-promote an affordance into authority."},
    "individuality": {"status": "SUBSTRATE_INSUFFICIENT", "activation": "No source-neutral ACTIVE/INACTIVE disposition context exists after retired V1 channels are excluded.", "risk": "candidate-local CLOSE-02Z is individuality variation, not individuality authority."},
}


STATE_OPPORTUNITY_MAP = {
    "physiology_nonhard": "ARCHITECTURE_EVIDENCE_INSUFFICIENT: hard recovery is separate; current non-hard state has no established categorical activation semantics.",
    "temporal_expectation": "INTERNAL_STATE_SUFFICIENT for existing temporal preparation/WAIT relevance when owner status/window semantics are met; an external opportunity may alter candidate specification but is not universally required.",
    "habit_routine": "BOTH_REQUIRED: owner routine eligibility and policy-visible current binding are both needed for a routine proposal.",
    "development_practice": "BOTH_REQUIRED: selected/valid owner goal plus current policy-visible capability/observation parameterization.",
    "relationship_social": "BOTH_REQUIRED: relationship/context state plus policy-visible matching social opportunity/cue.",
    "memory_recall": "ARCHITECTURE_EVIDENCE_INSUFFICIENT: recall may specify candidates, but no generic activation rule is qualified.",
    "environment_opportunity": "OPPORTUNITY_SUFFICIENT_FOR_CANDIDATE_AVAILABILITY_ONLY; not sufficient for motivational-context activation.",
    "individuality": "ARCHITECTURE_EVIDENCE_INSUFFICIENT: no active disposition context exists.",
}


RESOLUTION_FAMILIES = {
    "L1_incumbent_engagement_with_persistence": "Evaluate only owner revalidation, hard interruption, and starvation/initial-election boundary; no timeout or priority may be added.",
    "L2_categorical_context_election": "Evaluate whether a current owner-independent categorical resolver exists. Owner labels, source order, and numeric local state are forbidden as resolvers.",
    "L3_stochastic_context_election_plus_persistence": "Evaluate only as residual genuine indifference. Reject if it would routinely decide meaningful simultaneously active contexts.",
    "L4_common_categorical_preemption": "Hard authority remains unconditional. A non-hard preemption class needs one owner-independent meaning; absent that, do not infer it.",
    "L5_common_behavioral_control_claim": "Analyze only if categorical families fail; no number, coefficient, or normalization may be invented.",
}


def supported_one(channel: Any) -> bool:
    return isinstance(channel, dict) and channel.get("status") == "SUPPORTED" and float(channel.get("order", 0.0)) > 0.0


def load_decisions() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    traces = source_traces()
    decisions: list[dict[str, Any]] = []
    for name, info in traces.items():
        for line in Path(info["path"]).open():
            row = json.loads(line)
            competition = row.get("distributed_competition") or {}
            if not competition.get("views") or int(competition.get("admissible_candidate_count", 0)) < 2:
                continue
            decisions.append({"diagnostic": name, "tick": int(row["tick"]), "active_tick": int(row.get("active_ticks", row["tick"])), "row": row, "views": competition["views"]})
    return decisions, traces


def active_contexts(row: dict[str, Any], views: list[dict[str, Any]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    channel_contexts = {
        "development.active-intent": "development_practice",
        "memory.active-recall": "memory_recall",
        "relationship.active-partner-context": "relationship_social",
        "routine.active-context": "habit_routine",
    }
    for view in views:
        identity = str(view["identity"])
        for key, owner in channel_contexts.items():
            if supported_one((view.get("channels") or {}).get(key)):
                result[owner].add(identity)
    temporal = (row.get("temporal_proposals_or_modifiers") or {}).get("expectations") or []
    for view in temporal:
        if isinstance(view, dict) and view.get("status") == "ACTIVE":
            result["temporal_expectation"].add(str(view.get("recurrence_id", "unknown")))
    return dict(result)


def lock(root: Path, commit: str) -> None:
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("evidence_root_not_empty_for_lock")
    traces = source_traces()
    inventory = {"schema": "AS003F_CONTEXT_OWNER_INVENTORY_V1", "generated_at": now(), "architect_baseline": ARCHITECT_BASELINE, "governance_start_commit": commit, "owners": OWNER_INVENTORY, "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}}
    activation = {"schema": "AS003F_OWNER_ACTIVATION_AUDIT_V1", "generated_at": now(), "activation_semantic": "MOTIVATIONAL_CONTEXT_ACTIVE means that an owner has current sufficient authoritative evidence for one non-hard behavioral concern to participate in control. It is categorical and never encodes relative importance.", "common_states": {"activation": ["ACTIVE", "INACTIVE"], "evidence_quality": "UNKNOWN is separate evidence status, not a third activation rank; it cannot self-promote and cannot suppress first-experience candidate availability."}, "owners": ACTIVATION_AUDIT, "source_traces": {k: v["sha256"] for k, v in traces.items()}}
    opportunity = {"schema": "AS003F_STATE_OPPORTUNITY_ACTIVATION_MAP_V1", "generated_at": now(), "map": STATE_OPPORTUNITY_MAP, "universal_rule_rejected": "State/opportunity interaction differs by owner; no universal formula is adopted."}
    source_neutral = {"schema": "AS003F_SOURCE_NEUTRALITY_CONTRACT_V1", "generated_at": now(), "rule": "Context identity names a behavioral concern and its semantic scope, never the proposal source. Equivalent concerns deduplicate before any engagement decision; provenance remains audit/learning data only.", "prohibitions": ["proposal source authority", "source multiplicity", "insertion order", "owner rank", "numeric owner strength"], "duplicate_rule": "Two equivalent semantic contexts from different pathways cannot increase activation or authority."}
    identity = {"schema": "AS003F_CONTEXT_IDENTITY_CONTRACT_V1", "generated_at": now(), "included": ["context_kind", "semantic_scope", "relevant_opportunity_or_partner_identity_when_semantically_required", "owner_state_version", "body_schema_generation_only_when_context_meaning_depends_on_body"], "excluded": ["proposal_source", "insertion_index", "arbitrary_owner_rank", "numeric_activation_strength"], "persistence_rule": "An engaged identity is valid only while its owner revalidates ACTIVE and no hard interruption applies."}
    write_json(root, "AS003F_CONTEXT_OWNER_INVENTORY.json", inventory)
    write_json(root, "AS003F_OWNER_ACTIVATION_AUDIT.json", activation)
    write_json(root, "AS003F_STATE_OPPORTUNITY_ACTIVATION_MAP.json", opportunity)
    write_json(root, "AS003F_SOURCE_NEUTRALITY_CONTRACT.json", source_neutral)
    write_json(root, "AS003F_CONTEXT_IDENTITY_CONTRACT.json", identity)
    lock_doc = {"schema": LOCK_SCHEMA, "locked_at": now(), "architect_baseline": ARCHITECT_BASELINE, "governance_start_commit": commit, "owner_inventory_sha256": sha(root / "AS003F_CONTEXT_OWNER_INVENTORY.json"), "activation_audit_sha256": sha(root / "AS003F_OWNER_ACTIVATION_AUDIT.json"), "state_opportunity_map_sha256": sha(root / "AS003F_STATE_OPPORTUNITY_ACTIVATION_MAP.json"), "source_neutrality_contract_sha256": sha(root / "AS003F_SOURCE_NEUTRALITY_CONTRACT.json"), "context_identity_contract_sha256": sha(root / "AS003F_CONTEXT_IDENTITY_CONTRACT.json"), "activation_semantic": activation["activation_semantic"], "resolution_families": RESOLUTION_FAMILIES, "no_retuning_rule": "Owner activation, state/opportunity meanings, identity fields, and evaluated families cannot change after projection performance is known. A contradiction is reported, never optimized.", "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}, "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}}
    write_json(root, "AS003F_CONTEXT_RESOLUTION_LOCK.json", lock_doc)


def analyze(root: Path, commit: str) -> None:
    lock_doc = json.loads((root / "AS003F_CONTEXT_RESOLUTION_LOCK.json").read_text())
    if lock_doc.get("schema") != LOCK_SCHEMA:
        raise RuntimeError("context_lock_schema_mismatch")
    locked_hashes = {"owner_inventory_sha256": "AS003F_CONTEXT_OWNER_INVENTORY.json", "activation_audit_sha256": "AS003F_OWNER_ACTIVATION_AUDIT.json", "state_opportunity_map_sha256": "AS003F_STATE_OPPORTUNITY_ACTIVATION_MAP.json", "source_neutrality_contract_sha256": "AS003F_SOURCE_NEUTRALITY_CONTRACT.json", "context_identity_contract_sha256": "AS003F_CONTEXT_IDENTITY_CONTRACT.json"}
    for field, name in locked_hashes.items():
        if lock_doc[field] != sha(root / name):
            raise RuntimeError(f"context_lock_hash_mismatch:{name}")
    decisions, traces = load_decisions()
    counts: Counter[int] = Counter()
    owner_counts: Counter[str] = Counter()
    multi_owner_pairs: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    hard_interruptions = 0
    total_candidate_count = 0
    candidate_counts_by_context: Counter[str] = Counter()
    for decision in decisions:
        row = decision["row"]
        contexts = active_contexts(row, decision["views"])
        owners = sorted(contexts)
        for owner in owners:
            owner_counts[owner] += 1
            candidate_counts_by_context[owner] += len(contexts[owner])
        for i, left in enumerate(owners):
            for right in owners[i + 1:]:
                multi_owner_pairs[f"{left}+{right}"] += 1
        count = len(owners)
        counts[count] += 1
        critical = row.get("critical_recovery_context") or {}
        hard = bool(critical.get("critical_vars") or critical.get("active_recovery_needs"))
        hard_interruptions += int(hard)
        total_candidate_count += len(decision["views"])
        rows.append({"diagnostic": decision["diagnostic"], "tick": decision["tick"], "active_tick": decision["active_tick"], "active_context_count": count, "active_contexts": [{"identity": owner, "owner": OWNER_INVENTORY[owner]["owner"], "member_count": len(contexts[owner]), "members": sorted(contexts[owner])} for owner in owners], "incumbent_context_available": "UNKNOWN_NOT_RETAINED: ArbitrationState records capability continuity, not a source-neutral engaged-context identity", "hard_interruption": hard, "unknown_activation_cases": ["physiology_nonhard_not_categorical", "individuality_no_activation_path"]})
    simultaneous = {"schema": "AS003F_SIMULTANEOUS_CONTEXT_DATASET_V1", "generated_at": now(), "frozen_corpus": {"qualifying_decisions": len(decisions), "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}}, "method": "Only lock-defined source-neutral context signals were read from retained trace channels/transitions. Physiology non-hard, individuality, and unrecorded state are not inferred from numeric values or absent trace fields.", "summary": {"zero_active_contexts": counts[0], "one_active_context": counts[1], "multiple_active_contexts": sum(v for k, v in counts.items() if k > 1), "maximum_active_context_count": max(counts) if counts else 0, "hard_interruptions": hard_interruptions, "owner_activation_counts": dict(sorted(owner_counts.items())), "owner_pair_coactivation_counts": dict(sorted(multi_owner_pairs.items())), "mean_candidate_pool_size": total_candidate_count / len(decisions) if decisions else 0, "candidate_membership_counts": dict(sorted(candidate_counts_by_context.items()))}, "decisions": rows, "coverage_limits": ["No source-neutral incumbent-context identity is retained.", "No qualifying retained social current-tick proposal is expected from AS-003E and no social activation is inferred if absent.", "Temporal ACTIVE expectation may be absent or serialized incompletely; no unrecorded temporal state is reconstructed.", "Non-hard physiological activation cannot be inferred from existing numeric urgency without inventing a threshold.", "Individuality has no non-comparison activation path in the retained substrate."]}
    write_json(root, "AS003F_SIMULTANEOUS_CONTEXT_DATASET.json", simultaneous)
    single = {"schema": "AS003F_SINGLE_CONTEXT_PROJECTION_V1", "generated_at": now(), "method": "Static contract projection only; no candidate runs and no existing pool is modified.", "rule": "If exactly one source-neutral non-hard context is ACTIVE, it may identify its member subset as behaviorally relevant. Existing hard/admissibility authority remains outside. Immediate consequence evidence may compare existing candidates within that subset; UNKNOWN preserves first experience and cannot turn into low priority. CLOSE-02Z is only residual if more than one existing candidate still remains after a valid non-context comparison/resolution boundary.", "unresolved": "The frozen AS-003E projection shows the current supported-dominance comparator does not discriminate the immediate-consequence subset. This output does not repair or resurrect V1.", "observed_single_context_decisions": counts[1], "observed_zero_context_decisions": counts[0], "not_authorized": ["exclude unrelated base candidates globally", "assign a winner", "numeric relevance", "source merit"]}
    write_json(root, "AS003F_SINGLE_CONTEXT_PROJECTION.json", single)
    persistence = {"schema": "AS003F_PERSISTENCE_SWITCHING_AUDIT_V1", "generated_at": now(), "alternatives": {"G1_stateless_activation": {"finding": "would re-evaluate every tick and cannot preserve lived context continuity; retained corpus cannot prove it safe from thrashing."}, "G2_engaged_context_persistence": {"finding": "semantically supportable only with source-neutral identity plus owner revalidation; reduces repeated election after valid engagement but cannot solve first election or starvation."}, "G3_existing_continuity_only": {"finding": "ArbitrationState records capability continuity/switch behavior, not owner-neutral context identity; it cannot by itself establish context persistence."}}, "conclusion": "A minimal engagement state is required for context persistence, but any switch must be owner deactivation, verified completion/blocked event, hard interruption, or a future independently justified common non-hard condition. No arbitrary duration or switch penalty is allowed.", "corpus_limit": "No retained engaged-context identity means duration/switch frequency cannot be reconstructed honestly."}
    write_json(root, "AS003F_PERSISTENCE_SWITCHING_AUDIT.json", persistence)
    deactivation = {"schema": "AS003F_DEACTIVATION_INTERRUPT_MAP_V1", "generated_at": now(), "deactivation": {"physiology": "hard recovery remains owner/hard authority; non-hard categorical deactivation not yet established", "temporal": "expectation window completion/pass/status revision", "habit_routine": "owner procedure completion/invalid binding/verified denial", "development": "goal completion/invalidity/readiness withdrawal/verified outcome", "relationship_social": "partner opportunity disappears or owner context changes/verified result", "memory_recall": "owner working recall no longer current or item invalidation", "environment_opportunity": "affordance/cue disappears; this ends availability, not motivation", "individuality": "no context lifecycle established"}, "interruptions": {"unconditional_hard": ["critical physiology", "hard safety/admissibility", "Governance", "Embodiment impossibility", "existing qualified active recovery"], "nonhard": "No existing owner-independent CURRENT_CONTEXT_MUST_YIELD semantic was found. Owner deactivation/completion/verified blockage can end its own engagement; another owner cannot self-declare preemption."}}
    write_json(root, "AS003F_DEACTIVATION_INTERRUPT_MAP.json", deactivation)
    starvation = {"schema": "AS003F_STARVATION_THRASHING_ANALYSIS_V1", "generated_at": now(), "starvation": "Incumbent persistence can monopolize behavior whenever its owner remains ACTIVE and a rival is also ACTIVE. Existing evidence supplies no common non-hard release/preemption state; persistence therefore cannot be a complete simultaneous-context resolver.", "thrashing": "Stateless per-tick election risks alternation. Existing capability continuity cannot substitute for an engaged-context identity. Re-election randomness each tick is forbidden because it would make stochasticity motivational authority.", "allowed_release_evidence": ["owner deactivation", "verified completion", "verified blockage", "hard interruption", "future independently justified owner-neutral non-hard switch condition"], "prohibited_remedies": ["maximum duration", "numeric switch penalty", "source order", "numeric priority"]}
    write_json(root, "AS003F_STARVATION_THRASHING_ANALYSIS.json", starvation)
    multiple = sum(v for k, v in counts.items() if k > 1)
    family = f"""# AS-003F context-resolution family analysis

## Locked family assessment

### L1 — incumbent engagement with persistence

An engaged context may persist only while its owner revalidates `ACTIVE` and no hard interruption applies. This is a defensible continuity rule, but it cannot decide the initial no-incumbent case and cannot prevent starvation where an owner never deactivates. Retained traces do not contain a source-neutral engaged-context identity, so persistence duration is **UNKNOWN**, not inferred from capability continuity.

### L2 — categorical context election

No current UMBRA fact has one owner-independent categorical meaning that elects one of multiple simultaneously active non-hard contexts. Owner name, proposal source/order, local numerical urgency/readiness/confidence, and source multiplicity are prohibited. This family therefore cannot elect a context from existing substrate.

### L3 — stochastic election plus persistence

This can only be residual genuine indifference. The frozen dataset contains `{multiple}` decisions with more than one lock-visible context; where no incumbent/common resolver exists, stochastic election would decide their motivational boundary. Its semantic status is therefore **not supported as ordinary context authority**. CLOSE-02Z remains a candidate-level compatibility mechanism and is not automatically promoted to a context selector.

### L4 — common categorical preemption

Existing critical physiology, safety/admissibility, Governance, Embodiment, and qualified recovery are unconditional hard interruptions. No owner-independent non-hard preemption class exists. Letting each owner self-declare preemption would be disguised source priority.

### L5 — common behavioral-control claim

The exact unresolved proposition is: **among simultaneously ACTIVE non-hard contexts with no incumbent, no owner deactivation, no hard interruption, and no common categorical preemption, what common fact decides which context gains behavioral control?** Current UMBRA has no calibrated cross-system answer. A numeric score would require a new commensurable control claim and is not supplied here.
"""
    write_md(root, "AS003F_CONTEXT_RESOLUTION_FAMILY_ANALYSIS.md", family)
    projections = {"schema": "AS003F_FROZEN_CORPUS_PROJECTIONS_V1", "generated_at": now(), "lock_sha256": sha(root / "AS003F_CONTEXT_RESOLUTION_LOCK.json"), "summary": simultaneous["summary"], "families": {"L1": {"projection": "incumbent unavailable in retained trace; no valid numeric projection", "status": "CANNOT_RESOLVE_INITIAL_ELECTION_OR_STARVATION"}, "L2": {"projection": "no current common categorical election fact", "status": "UNRESOLVED"}, "L3": {"projection": "would be required whenever multiple active contexts lack an incumbent/resolver", "status": "REJECTED_AS_DE_FACTO_AUTHORITY_RISK"}, "L4": {"projection": "hard interruption observed/retained separately; no common non-hard preemption", "status": "UNRESOLVED"}, "L5": {"projection": "not projected; no common unit/calibration", "status": "NOT_SUPPORTED"}}, "immediate_consequence_pressure": "No projection alters AS-003E result: role-eligible consequence comparison remains 0/76216 relations. Context formation does not resurrect V1.", "no_tuning": True}
    write_json(root, "AS003F_FROZEN_CORPUS_PROJECTIONS.json", projections)
    generality = """# AS-003F generality review

The contract distinguishes owners and does not make physiology universally dominant. Temporal policy views, routines, development goals, social state, memory recall, and opportunity have different owner-specific activation prerequisites. Opportunity enables actions but is not itself motivation; SelfModel and WorldModel preserve bounded one-step consequence/selected-only learning roles; individuality remains a documented substrate gap rather than a fabricated activation claim.

The sealed A/B corpus realizes memory/development paths but underrepresents temporal, social, habit, and individuality activation. Static qualified semantics are enough to test whether the proposed identity/owner rules would apply to each; they do **not** establish population behavior. Any architecture that only works for physiology is rejected.
"""
    write_md(root, "AS003F_GENERALITY_REVIEW.md", generality)
    lifecycle = """# AS-003F context lifecycle contract

## Minimum representation

The common activation state is categorical `ACTIVE` or `INACTIVE`. `UNKNOWN` remains evidence quality, not an activation rank: it cannot self-promote, but it cannot suppress first-experience candidate availability. A separate persisted **engaged context identity** is needed only after a valid engagement decision; it is not a new numeric state machine.

## Lifecycle

1. An owner establishes `ACTIVE` from its own qualified state and policy-visible opportunity relation where that owner requires one.
2. A valid engagement establishes one source-neutral context identity and a bounded member subset of already-existing candidates.
3. Engagement persists while the owner remains `ACTIVE`, identity remains valid, and no hard interruption occurs.
4. Owner deactivation, verified completion, verified blockage, or hard authority ends engagement. The previous context may resume only after owner revalidation; no counterfactual learning occurs.
5. No candidate proposal or source provenance can create activation, engagement, or preemption authority.

## Open boundary

When multiple non-hard contexts are `ACTIVE` with no incumbent and no common categorical preemption condition, this lifecycle deliberately does not elect one. Resolving that state requires an additional common semantic; no score, timeout, source priority, or stochastic default is licensed.
"""
    write_md(root, "AS003F_CONTEXT_LIFECYCLE_CONTRACT.md", lifecycle)
    contract = """# AS-003F replacement-contract disposition

## Supported portion

Owner-derived categorical activation and a persisted engaged-context identity are semantically bounded: activation says only that a specific non-hard behavioral concern may participate, while engagement preserves that concern across ticks until owner deactivation, verified completion/blocked state, or hard interruption. The contract preserves source neutrality, first experience, selected-only learning, candidate generation, hard authority, and CLOSE-02Z candidate identity.

## Terminal boundary

The contract cannot select among simultaneously ACTIVE non-hard contexts with no incumbent. Existing UMBRA provides no owner-independent categorical election or non-hard preemption fact. Persistence reduces re-election only after engagement; it does not solve initial election and can monopolize control. Candidate-level CLOSE-02Z would become the context selector in this state and is therefore not a supported remedy.

## Exact missing primitive

`CURRENT_NONHARD_CONTEXT_CONTROL_CLAIM`: one source-neutral, owner-independent fact with a single cross-system meaning that can decide which of otherwise simultaneous ACTIVE non-hard contexts may gain behavioral control now. It must have bounded provenance, explicit first-experience/UNKNOWN semantics, reproducibility across restart/migration, and owner-independent revision/qualification. No numerical magnitude, coefficient, source rank, planner, global utility, or arbitrary timeout is specified or authorized.
"""
    write_md(root, "AS003F_REPLACEMENT_CONTRACT.md", contract)
    verdict = {"schema": "AS003F_VERDICT_V1", "generated_at": now(), "primary_verdict": "AS003F_SIMULTANEOUS_CONTEXT_RESOLUTION_PRIMITIVE_REQUIRED", "recommendation": None, "disposition": {"activation": "SUPPORTED_AS_CATEGORICAL_OWNER_DERIVED_SEMANTIC_WITH_ACTIVE_INACTIVE_ONLY", "persistence": "SUPPORTED_ONLY_AFTER_VALID_ENGAGEMENT; INSUFFICIENT_FOR_INITIAL_ELECTION_OR_STARVATION", "interruption": "HARD_AUTHORITY_PRESERVED; NO_COMMON_NONHARD_PREEMPTION", "simultaneous_context_resolution": "MISSING_COMMON_SEMANTIC", "stochasticity": "REJECTED_AS_DEFAULT_CONTEXT_AUTHORITY", "common_control_claim": "REQUIRED_IF_NO_OWNER_INDEPENDENT_CATEGORICAL_RESOLVER_CAN_BE_ESTABLISHED", "arbitrary_weighting_risk": "NUMERIC_OR_SOURCE_ORDERING_REMAINS_REJECTED"}, "missing_proposition": "Among several simultaneously ACTIVE, non-hard, non-deactivated contexts with no incumbent and no common categorical preemption condition, what common fact determines which gains behavioral control?", "basis": {"qualifying_decisions": len(decisions), "active_context_summary": simultaneous["summary"], "role_partition_result": "0/76216 supported relations and 2647/2647 full frontiers retained from AS003E", "corpus_limits": simultaneous["coverage_limits"]}, "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}, "source_trace_sha256": {k: v["sha256"] for k, v in traces.items()}}
    write_json(root, "AS003F_VERDICT.json", verdict)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--lock", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    if args.lock == args.analyze:
        raise SystemExit("choose_exactly_one_of_lock_or_analyze")
    if args.lock:
        lock(args.evidence_root, args.commit)
    else:
        analyze(args.evidence_root, args.commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
