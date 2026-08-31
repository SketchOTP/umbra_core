#!/usr/bin/env python3
"""Seal AS-003D static-audit and replan artifacts without touching production."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        offset = 0
        while offset < len(content):
            count = os.write(fd, content[offset:])
            if count <= 0:
                raise OSError("short_write")
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def write_json(path: Path, value: Any) -> None:
    durable(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def write_md(path: Path, text: str) -> None:
    durable(path, text.encode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    root = args.evidence_root
    pairwise = json.loads((root / "AS003D_PAIRWISE_BLOCKER_DECOMPOSITION.json").read_text())
    coverage = json.loads((root / "AS003D_CHANNEL_COVERAGE_ANALYSIS.json").read_text())
    homeostasis = json.loads((root / "AS003D_HOMEOSTATIC_TRADEOFF_ANALYSIS.json").read_text())
    taxonomy = json.loads((root / "AS003D_INCOMPARABILITY_TAXONOMY.json").read_text())
    ablation = json.loads((root / "AS003D_CAUSAL_ABLATION_MATRIX.json").read_text())
    stochastic = json.loads((root / "AS003D_STOCHASTIC_RESOLUTION_AUDIT.json").read_text())
    source_hashes = pairwise["source_trace_sha256"]

    semantics = {
        "schema": "AS003D_EXISTING_ENDOGENOUS_SEMANTICS_AUDIT_V1",
        "generated_at": now(),
        "start_commit": args.commit,
        "production_changes": 0,
        "organism_runs": 0,
        "items": [
            {
                "semantic": "Physiology.vector_urgency and per-dimension distance/criticality",
                "source": "umbra_core/physiology.py:131-142; umbra_core/distributed_competition.py:_physiology_channels",
                "within_proposition_magnitude": "YES; each homeostatic dimension has its own bounded urgency/distance semantics.",
                "cross_candidate_comparable": "YES within the same dimension; retained views compare conservative one-step distance.",
                "cross_family_commensurable": "NO evidence; AS-002 explicitly forbids a cross-family sum.",
                "constitutional_status": "CONSTITUTIONAL for bounds/effects; protected hard critical and active recovery remain outside ordinary competition.",
                "can_bias_without_global_utility": "Only as separate directional evidence today; no retained rule resolves conflicts among dimensions.",
            },
            {
                "semantic": "SelfModel verified capability-support envelopes",
                "source": "umbra_core/self_model/engine.py:candidate_consequence_view",
                "within_proposition_magnitude": "YES for success/progress/duration when verified support exists.",
                "cross_candidate_comparable": "Sometimes; retained coverage has 58.9% pairwise shared support and 24.6% one-sided applicability across SelfModel channels.",
                "cross_family_commensurable": "NO.",
                "constitutional_status": "LEARNED, verified-outcome-bound, pure preselection view.",
                "can_bias_without_global_utility": "Evidence may constrain a relation but V1 requires it to be jointly supported with every other applicable proposition.",
            },
            {
                "semantic": "WorldModel one-step transition effects",
                "source": "umbra_core/world_model/engine.py:candidate_consequence_view",
                "within_proposition_magnitude": "YES for learned action/entity effect fields.",
                "cross_candidate_comparable": "Rarely; retained WorldModel shared-support rate is 8.68% and one-sided applicability rate is 48.25%.",
                "cross_family_commensurable": "NO.",
                "constitutional_status": "LEARNED, selected-only verified-outcome revision; pure view.",
                "can_bias_without_global_utility": "Not under universal joint-support V1 in the observed corpus; source remains valid but mostly produces semantic incomparability.",
            },
            {
                "semantic": "Continuity, active intent, and active recall context",
                "source": "umbra_core/arbitration.py:continuity_channels; umbra_core/runtime.py:contextual_channels",
                "within_proposition_magnitude": "YES as candidate membership/continuity propositions.",
                "cross_candidate_comparable": "YES; all retained instances are supported and discriminatory for continuity/context in 45.67% of ordered pairs.",
                "cross_family_commensurable": "NO.",
                "constitutional_status": "Contextual/learned state, not a proposal-source priority.",
                "can_bias_without_global_utility": "It creates genuine conflict with physiological and other propositions; V1 cannot negotiate that conflict.",
            },
            {
                "semantic": "Individuality dispositions",
                "source": "umbra_core/individuality/engine.py:candidate_evidence_channels",
                "within_proposition_magnitude": "YES only where verified disposition support exists.",
                "cross_candidate_comparable": "Partial; retained family support is 24.92% and UNKNOWN is 75.08%.",
                "cross_family_commensurable": "NO.",
                "constitutional_status": "Learned persistent individuality; old apply_modifiers scalar compatibility path is not ordinary competition authority in the frozen path.",
                "can_bias_without_global_utility": "V1 preserves it but frequently turns it into an UNKNOWN blocker rather than usable influence.",
            },
            {
                "semantic": "Temporal expectations and verified fallback",
                "source": "umbra_core/arbitration.py:temporal_channels",
                "within_proposition_magnitude": "YES per recurrence/fallback proposition.",
                "cross_candidate_comparable": "Potentially within a temporal proposition; absent in the qualifying frozen corpus.",
                "cross_family_commensurable": "NO.",
                "constitutional_status": "Learned/verified temporal state; static audit only.",
                "can_bias_without_global_utility": "No retained evidence establishes a conflict resolver for it.",
            },
        ],
        "conclusion": "The codebase contains bounded endogenous magnitudes within coherent propositions, but no currently authorized cross-proposition tradeoff primitive. The audit does not authorize one.",
    }
    write_json(root / "AS003D_EXISTING_ENDOGENOUS_SEMANTICS_AUDIT.json", semantics)

    write_md(root / "AS003D_PRIOR_ART_REPLAN_BOUNDARY.md", """# AS-003D bounded prior-art replan boundary

## Sources checked

- Paul Cisek, *Cortical mechanisms of action selection: the affordance competition hypothesis* (2007), https://pmc.ncbi.nlm.nih.gov/articles/PMC2440773/. The paper describes parallel specification of currently available actions, with multiple information sources biasing their competition until one response is selected. It does not require serial planning.
- User-supplied many-objective source: He et al., *Many-Objective Optimization Using Adaptive Differential Evolution with a New Ranking Method* (2014), https://onlinelibrary.wiley.com/doi/10.1155/2014/259473. The publisher page was not machine-readable in this review; it is retained only for its stated structural theme that nondominance rises as independent objectives increase.
- Nevai, Waite, and Passino, *State-dependent choice and ecological rationality* (2007), https://pubmed.ncbi.nlm.nih.gov/17467743/. Its abstract discusses state-dependent adjustment among competing demands; it is reference-only and does not supply a UMBRA mechanism.

## Bounded conclusions

The sources support only these boundary observations: autonomous action selection must choose among currently available alternatives; multiple state and environmental factors can influence a competition; and universal nondominance becomes structurally uninformative when many independent dimensions remain active. They do **not** validate a UMBRA equation, neural simulation, utility function, or a particular resolver.

## Explicit non-imports

No epsilon dominance, hypervolume, crowding distance, reference vector, objective clustering, voting, RL, active inference, POMDP, MPC, planner, rollout, neural imitation, global expected utility, source priority, or arbitrary cross-channel coefficient is adopted. This review changes no production code and recommends no dependency.

## Recheck trigger

Revisit only after the Architect authorizes a separately specified action-selection primitive and its evidence/constitutional boundaries. External work cannot substitute for an explicit UMBRA contract.
""")
    write_md(root / "AS003D_AS002_ASSUMPTION_REVIEW.md", """# AS-003D review of AS-002 premises

| AS-002 premise | Disposition | Retained evidence |
| --- | --- | --- |
| Evidence channels remain separate. | SUPPORTED_WITH_LIMIT | The frozen views preserve per-key status/order/provenance; separation alone does not produce selection pressure. |
| No cross-channel arithmetic. | SUPPORTED_WITH_LIMIT | Static source has no ordinary scalar authority, but the remaining rule cannot resolve observed cross-proposition conflict. |
| UNKNOWN blocks unsupported elimination. | SUPPORTED_WITH_LIMIT | It preserves first experience; every qualifying decision also had an epistemic blocker. |
| One-sided applicability blocks dominance. | SUPPORTED_WITH_LIMIT | It prevents false merit, but every qualifying decision contained semantic incomparability. |
| Elimination requires no-worse-everywhere plus a strict improvement. | DISPROVEN_OPERATIONALLY | Zero relations in 76,216 ordered retained pairs; 2,645/2,647 decisions also contain motivational conflict. |
| Candidate-local stochasticity resolves genuine residual nondominance. | DISPROVEN_OPERATIONALLY | It resolved all 2,647 qualifying decisions and distributed evidence changed no winner. |
| Learned/internal evidence can materially constrain ordinary action. | DISPROVEN_OPERATIONALLY | Views reach comparison, but no candidate was eliminated and the selected identity always matched the stochastic-only full-pool shadow. |

The review does not invalidate AS-002's protections against arbitrary scalar summation. It retires its V1 universal-supported-dominance predicate as a forward ordinary-selection candidate.
""")
    write_md(root / "AS003D_ARCHITECTURE_CANDIDATES.md", """# AS-003D architecture-family boundary

This is a taxonomy, not implementation authority.

## 1. Retain V1 supported dominance plus stochastic frontier resolution

**Rejected by retained evidence.** It keeps propositions noncommensurable and preserves UNKNOWN, but all 2,647 qualifying decisions reached the full frontier and stochasticity selected every ordinary result. It therefore makes learned/internal evidence observational rather than causal in this corpus.

## 2. Fixed or context-priority hierarchy

**Rejected inside this directive.** It would resolve conflicts by assigning an ordering to needs, sources, or channels. That is an explicit priority semantics and risks source priority; frozen evidence does not establish a constitutionally valid hierarchy.

## 3. Arbitrary weighted or global utility aggregation

**Rejected inside this directive.** It would make heterogeneous propositions commensurable via authored coefficients or a global objective, exactly the AS-001 boundary that remains prohibited.

## Missing primitive to investigate separately

Any future family would need an explicit, bounded **endogenous conflict-resolution primitive** rather than merely a renamed score. It would have to state: (a) the distinct within-proposition quantities that interact; (b) the state/verified-learning origin of each influence; (c) how opposite supported effects change a candidate relation without a global utility; (d) what UNKNOWN withholds; (e) how first experience remains possible; (f) how one existing candidate emerges; (g) how candidate-local stochasticity remains residual rather than de facto authority; and (h) how persistence, migration, source neutrality, hard safety, active/critical recovery, Governance, Embodiment, and selected-only learning stay protected.

No member of this taxonomy is an AS-003E contract. The retained data establishes V1 insufficiency, not a uniquely validated replacement.
""")
    write_md(root / "AS003D_REPLACEMENT_CONTRACT.md", """# AS-003D replacement-contract disposition

## No replacement contract supported

`AS003D` does not authorize or support an implementation-ready replacement contract. The frozen evidence rejects the V1 universal no-worse predicate as an ordinary selector, but it cannot choose among non-equivalent resolver semantics without inventing a new constitutional relation.

## Exact future decision boundary

A separately authorized contract exploration must decide whether a bounded endogenous conflict-resolution primitive can be specified without arbitrary cross-system coefficients, global utility, source priority, planning, hidden future truth, or loss of UNKNOWN/first-experience protections. It must be testable against the frozen AS-003C corpus before production implementation. This file is not a successor recommendation and authorizes no code change.
""")
    verdict = {
        "schema": "AS003D_VERDICT_V1",
        "generated_at": now(),
        "primary_verdict": "AS003D_SUPPORTED_DOMINANCE_STRUCTURALLY_INSUFFICIENT",
        "successor_recommendation": None,
        "v1_forward_status": "RETIRED_AS_FORWARD_ORDINARY_SELECTION_CANDIDATE_PENDING_NEW_ARCHITECT_AUTHORITY",
        "basis": {
            "qualifying_decisions": 2647,
            "ordered_pairs": 76216,
            "supported_dominance_relations": 0,
            "full_frontier_decisions": 2647,
            "stochastic_resolution_decisions": 2647,
            "distributed_changed_winner": 0,
            "motivational_tradeoff_decisions": 2645,
            "epistemic_incomparability_decisions": 2647,
            "semantic_incomparability_decisions": 2647,
            "physiology_only_decisions_with_relation": 2563,
            "physiology_only_decision_rate_percent": 96.826596,
        },
        "interpretation": "Evidence substrate and applicability fragmentation contribute, but neither is sufficient as the primary explanation: genuine well-supported cross-proposition conflict is present in 99.924443% of decisions, and the V1 requirement of universal joint support plus no-worse-everywhere suppresses every ordinary relation.",
        "not_established": [
            "a replacement architecture contract",
            "a valid weight or coefficient scheme",
            "a source hierarchy",
            "a planner or rollout",
            "a future qualification successor",
        ],
        "integrity": {
            "production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0,
            "retries": 0, "reseeds": 0, "as003c_source_trace_sha256": source_hashes,
        },
    }
    write_json(root / "AS003D_VERDICT.json", verdict)
    required = [
        "AS003D_FROZEN_COMPETITION_DATASET_INDEX.json",
        "AS003D_PAIRWISE_BLOCKER_DECOMPOSITION.json",
        "AS003D_CHANNEL_COVERAGE_ANALYSIS.json",
        "AS003D_HOMEOSTATIC_TRADEOFF_ANALYSIS.json",
        "AS003D_INCOMPARABILITY_TAXONOMY.json",
        "AS003D_CAUSAL_ABLATION_MATRIX.json",
        "AS003D_STOCHASTIC_RESOLUTION_AUDIT.json",
        "AS003D_EXISTING_ENDOGENOUS_SEMANTICS_AUDIT.json",
        "AS003D_PRIOR_ART_REPLAN_BOUNDARY.md",
        "AS003D_AS002_ASSUMPTION_REVIEW.md",
        "AS003D_ARCHITECTURE_CANDIDATES.md",
        "AS003D_REPLACEMENT_CONTRACT.md",
        "AS003D_VERDICT.json",
    ]
    manifest = {
        "schema": "AS003D_FINAL_EVIDENCE_MANIFEST_V1",
        "generated_at": now(),
        "start_commit": args.commit,
        "required_files": {name: sha(root / name) for name in required},
        "source_trace_sha256": source_hashes,
        "interim_manifest_sha256": sha(root / "AS003D_INTERIM_DERIVATIVE_EVIDENCE_MANIFEST.json"),
        "durability": "file fsync, atomic rename, directory fsync, readback SHA-256",
        "integrity": {"production_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0},
    }
    write_json(root / "AS003D_EVIDENCE_MANIFEST.json", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
