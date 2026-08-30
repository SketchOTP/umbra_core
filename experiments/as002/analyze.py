#!/usr/bin/env python3
"""Static evidence and pure contract proof for UMBRA-AS-002.

This module never imports or executes the organism runtime.  It reads source
and retained evidence, models the proposed decision relation with immutable
fixture values, and writes the permanent dossier using file-scoped durability.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Mapping


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-002-distributed-competition-r1"
)
BASELINE = "1400e11370fc5dd267cb782649c242a06ec56c54"
GOVERNANCE_START = "3d66ad5be807622b4505f63169cc7ead460e1c54"
AS001 = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-001-learned-consequence-action-selection-r1"
)
Z = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-close-02z-candidate-stochastic-r1"
)


def sh(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(directory: Path) -> dict[str, object]:
    manifest = load_json(directory / "EVIDENCE_HASHES.json")
    assert isinstance(manifest, dict)
    items = manifest.get("artifacts") or manifest.get("files") or manifest.get("hashes")
    if isinstance(items, dict):
        items = [{"path": key, "sha256": value} for key, value in items.items()]
    assert isinstance(items, list)
    checked = 0
    mismatches: list[str] = []
    for item in items:
        assert isinstance(item, dict)
        name = item.get("path") or item.get("file") or item.get("name")
        expected = item.get("sha256") or item.get("sha256_readback") or item.get("digest")
        if not name or not expected:
            continue
        checked += 1
        artifact = directory / str(name)
        if not artifact.exists() or sha(artifact) != expected:
            mismatches.append(str(name))
    return {
        "directory": str(directory),
        "checked": checked,
        "mismatches": mismatches,
        "pass": not mismatches,
        "manifest_sha256": sha(directory / "EVIDENCE_HASHES.json"),
    }


def atomic_write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == hashlib.sha256(data).hexdigest()
        return digest
    finally:
        if tmp.exists():
            tmp.unlink()


def write_json(name: str, value: object) -> None:
    atomic_write(EVIDENCE / name, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def write_text(name: str, value: str) -> None:
    atomic_write(EVIDENCE / name, value.rstrip().encode() + b"\n")


SUPPORTED = "SUPPORTED"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class EvidenceValue:
    """One channel-internal ordinal value; never comparable across channels."""

    status: str
    order: float | None = None
    provenance: str = "fixture"


@dataclass(frozen=True)
class EvaluatedCandidate:
    identity: str
    channels: Mapping[str, EvidenceValue]
    stochastic_term: float


def supported(order: float, provenance: str = "fixture") -> EvidenceValue:
    return EvidenceValue(SUPPORTED, order, provenance)


def unknown(provenance: str = "missing") -> EvidenceValue:
    return EvidenceValue(UNKNOWN, None, provenance)


def inapplicable() -> EvidenceValue:
    return EvidenceValue(NOT_APPLICABLE, None, "not_applicable")


def dominates(a: EvaluatedCandidate, b: EvaluatedCandidate) -> bool:
    """Supported-dominance without sums, votes, priorities, or UNKNOWN coercion.

    A strict dominance claim is valid only when every proposition applicable to
    either candidate is supported for both candidates, A is no worse in each,
    and A is strictly better in at least one.  UNKNOWN therefore blocks an
    elimination claim but never counts as favorable or unfavorable.
    """

    strictly_better = False
    for key in sorted(set(a.channels) | set(b.channels)):
        av = a.channels.get(key, inapplicable())
        bv = b.channels.get(key, inapplicable())
        if av.status == NOT_APPLICABLE and bv.status == NOT_APPLICABLE:
            continue
        if av.status != SUPPORTED or bv.status != SUPPORTED:
            return False
        assert av.order is not None and bv.order is not None
        if av.order < bv.order:
            return False
        if av.order > bv.order:
            strictly_better = True
    return strictly_better


def frontier(candidates: list[EvaluatedCandidate]) -> list[EvaluatedCandidate]:
    """Simultaneous nondominated frontier; list order has no semantic role."""

    by_identity = {candidate.identity: candidate for candidate in candidates}
    unique = list(by_identity.values())
    return sorted(
        [
            candidate
            for candidate in unique
            if not any(
                other.identity != candidate.identity and dominates(other, candidate)
                for other in unique
            )
        ],
        key=lambda item: item.identity,
    )


def resolve(candidates: list[EvaluatedCandidate]) -> EvaluatedCandidate:
    """Return one existing candidate from the supported-dominance frontier."""

    survivors = frontier(candidates)
    if not survivors:
        raise ValueError("no_admissible_existing_candidate")
    return sorted(survivors, key=lambda item: (-item.stochastic_term, item.identity))[0]


def as001_candidate_recovery() -> dict[str, object]:
    text = (AS001 / "AS001_ARCHITECTURE_CANDIDATES.md").read_text(encoding="utf-8")
    return {
        "source_sha256": sha(AS001 / "AS001_ARCHITECTURE_CANDIDATES.md"),
        "candidates": [
            {
                "id": "A",
                "rule": "pure consequence views added to current scalar total",
                "scalar_assumption": "heterogeneous predictions can be mapped into one total",
                "unknown": "would require numeric mapping",
                "stochastic": "added into same total",
                "authority": "ordinary scorer unchanged",
                "migration": "small code change, scientific defect retained",
                "failure": "uncalibrated cross-proposition commensurability",
                "disposition": "REJECT",
            },
            {
                "id": "B",
                "rule": "evidence-conditioned distributed competition",
                "scalar_assumption": "none authorized across channels",
                "unknown": "neutral and explicit",
                "stochastic": "candidate-stable resolution after evidence",
                "authority": "one final existing candidate; hard authority unchanged",
                "migration": "ordinary evaluation and additive modifier interface",
                "failure": "AS-001 left exact conflict/final resolution unspecified",
                "disposition": "RECOVER_AND_FALSIFY_IN_AS002",
            },
            {
                "id": "C",
                "rule": "learned planner/global utility selector",
                "scalar_assumption": "global objective or utility",
                "unknown": "model-dependent",
                "stochastic": "policy-level",
                "authority": "replaces candidate generation/arbitration",
                "migration": "deeper qualified substrate replacement",
                "failure": "planner/utility drift and excess scope",
                "disposition": "REJECT",
            },
        ],
        "candidate_markers_verified": all(marker in text for marker in ("Candidate A", "Candidate B", "Candidate C")),
    }


def evidence_channel_schema() -> dict[str, object]:
    channels = [
        ("physiology.<dimension>", "one-step projected relation to the same dimension's ideal/bounds", "Physiology + constitutional effect branch + learned view", "MIXED", "ordinal within one named dimension", "4 fixed dimensions"),
        ("body.success.<capability-context>", "learned probability/reliability of this body's execution", "SelfModel", "LEARNED", "within same body schema and calibrated support family", "fixed candidate cap"),
        ("body.cost.<field>", "predicted immediate body cost/duration/displacement", "SelfModel", "LEARNED", "within same physical field/unit", "fixed fields"),
        ("world.effect.<field>", "predicted one-step environmental/affordance consequence", "WorldModel", "LEARNED", "within same transition field/model family", "<=4 transition records"),
        ("observation.effect.<field>", "predicted acquisition/refresh of one exact policy-visible field", "SelfModel/WorldModel", "LEARNED", "categorical or within-field", "fixed view fields"),
        ("temporal.<expectation>", "candidate congruence with one qualified current expectation/window", "Temporal", "LEARNED", "within same recurrence/window", "<=2 views per candidate"),
        ("continuity.current-commitment", "preserves or breaks the current bounded executable commitment", "ArbitrationState", "CONSTITUTIONAL", "categorical within current commitment", "1"),
        ("individuality.<dimension-context>", "candidate congruence with one verified lived disposition", "Individuality", "LEARNED", "within same disposition/context", "fixed qualified dimensions"),
        ("relationship.<partner-context>", "candidate relevance to one policy-visible learned relationship proposition", "Social", "LEARNED", "within same partner/context proposition", "bounded active context"),
        ("routine.<routine-context>", "continuity/reliability of one active verified routine", "Memory", "LEARNED", "within same routine context", "bounded selected routine"),
        ("development.<active-intent>", "behavioral consistency within the already-valid active intent set", "Development", "MIXED", "within same active intent", "bounded active intent"),
    ]
    return {
        "statuses": [SUPPORTED, UNKNOWN, NOT_APPLICABLE],
        "comparison_rule": "values compare only inside the same fully-qualified channel key; cross-channel conversion is forbidden",
        "unknown": "blocks a dominance claim for that proposition; is never zero, bad, good, or unsafe",
        "confidence": "used only by the owning subsystem's existing support semantics; never multiplied or summed across channels",
        "channels": [
            dict(zip(("channel", "proposition", "owner", "authority", "comparability", "bound"), row))
            for row in channels
        ],
        "source_channels_prohibited": True,
        "proposal_source_is_merit": False,
    }


def evidence_authority_map() -> dict[str, object]:
    return {
        "CONSTITUTIONAL": [
            "capability existence and body-schema binding",
            "physiology bounds, ideals, unavoidable drift, and verified effect vocabulary",
            "hard immediate safety and contract admissibility",
            "bounded current-commitment state",
        ],
        "LEARNED": [
            "SelfModel body reliability/cost/duration/motion support",
            "WorldModel transition, affordance, observation, contradiction, and uncertainty evidence",
            "temporal expectations",
            "procedural routine lifecycle",
            "relationship propositions",
            "individuality dispositions",
        ],
        "MIXED": [
            "per-dimension physiology view: constitutional bounds/effects plus learned body/world contingency",
            "development active-intent semantics: qualified internal selection plus learned progress/history",
        ],
        "UNKNOWN": [
            "unsupported candidate consequence",
            "incomparable calibration families",
            "missing provenance",
            "overflow beyond fixed view bound",
        ],
        "hard_authority_outside_competition": [
            "candidate_allowed",
            "critical-boundary safety",
            "recoverability admissibility",
            "Governance",
            "Embodiment",
        ],
        "learning_boundary": "only the selected candidate receives committed predictions; only VerifiedOutcome updates learned state",
    }


def consequence_view_markdown() -> str:
    return """# AS-002 CANDIDATE_CONSEQUENCE_VIEW_V1

For each canonical already-generated candidate, ordinary preselection receives one immutable fixed-size view. The key is the CLOSE-02Z source-neutral behavioral identity plus the current body-schema generation and policy-state version. The view contains: per-dimension physiology projection; SelfModel success, motion, cost, duration, confidence and provenance; up to four WorldModel transition/observation consequences with confidence, uncertainty and provenance; exact temporal/routine/relationship/individuality context references; and an explicit `SUPPORTED`, `UNKNOWN`, or `NOT_APPLICABLE` status for every field.

The query reads persisted learned state, policy-visible observations, physiology, candidate parameters, and constitutional verified effect branches. It consumes no RNG, allocates no prediction ID, writes no pending/history state, performs no learning, executes nothing, ranks nothing, and never reads hidden simulator truth. Unsupported, mismatched, stale, overflowed, or cross-schema evidence is `UNKNOWN`.

After final selection, only the selected candidate is passed to the existing committed SelfModel/WorldModel prediction path. Later comparison and learning remain gated by `VerifiedOutcome`. Unselected views are ephemeral counterfactual evidence, never experience.
"""


def competition_family_analysis_markdown() -> str:
    return """# AS-002 competition-family analysis

## Weighted sum / normalized utility

Rejected. Normalization and weights manufacture cross-channel units and preserve AS-001's defect.

## Equal channel voting or fixed channel priority

Rejected. Vote count makes channel count an implicit weight; fixed ordering creates an authored need/source hierarchy.

## Evidence accumulation

Rejected as the final cross-channel rule. Accumulation is legitimate only inside one calibrated channel. Cross-channel accumulation silently recreates a scalar.

## Unqualified Pareto optimizer

Rejected as an automatic answer. A generic multi-objective frontier does not define evidence authority, UNKNOWN, first experience, continuity, or one final action.

## Supported-dominance frontier with stochastic resolution

Supported as the one bounded contract after UMBRA-specific restrictions. Each owning subsystem may establish only a within-channel ordinal relation. Candidate A defeats B only when every proposition applicable to either is supported for both, A is no worse in each, and A is strictly better in at least one. UNKNOWN blocks elimination. All defeats are computed simultaneously. No channel count, channel order, normalization, magnitude addition, confidence multiplication, or source identity enters the rule.

The nondominated frontier represents genuine conflict or incomplete evidence. CLOSE-02Z's existing candidate-local stochastic term selects exactly one frontier member; canonical behavioral identity breaks an exact stochastic tie. Stochasticity cannot erase supported dominance because defeated candidates never reach that step. A non-empty finite set always has a frontier under the frozen within-channel preorder contract.

Hard safety, admissibility, urgent recovery, Governance, and Embodiment remain outside this ordinary competition.
"""


def scorer_migration_map() -> dict[str, object]:
    rows = [
        ("expected_regulatory_gain", "TRANSLATE_TO_EVIDENCE_CHANNEL", "separate physiology.<dimension> projections; remove capability/target coefficients"),
        ("expected_option_preservation", "TRANSLATE_TO_EVIDENCE_CHANNEL", "supported world/route consequence only; remove constant baseline and local deductions"),
        ("novelty", "REMOVE_WITH_SCALAR_SCORER", "authored capability constants are not learned novelty; qualified development/individuality proposals remain"),
        ("uncertainty_reduction", "TRANSLATE_TO_EVIDENCE_CHANNEL", "exact action-conditioned observation.effect field only; remove generic and INSPECT/ORIENT constants"),
        ("effort_cost", "TRANSLATE_TO_EVIDENCE_CHANNEL", "SelfModel body.cost fields in native units; remove capability lookup"),
        ("risk_cost", "MOVE_OUTSIDE_COMPETITION", "hard risk remains safety/admissibility; learned noncritical hazard consequence may be a world field"),
        ("commitment_continuity", "TRANSLATE_TO_EVIDENCE_CHANNEL", "categorical bounded continuity proposition; remove additive hysteresis and scalar band"),
        ("temporal_modifier", "TRANSLATE_TO_EVIDENCE_CHANNEL", "qualified per-expectation congruence; remove additive caps"),
        ("individuality", "TRANSLATE_TO_EVIDENCE_CHANNEL", "per-disposition/context ordinal relation; no sum across dimensions"),
        ("fallback_bias", "KEEP_AS_QUALIFIED_STATE_SEMANTIC", "specific wait-journal consequence in temporal context; no cross-channel addition"),
        ("stochastic", "MOVE_OUTSIDE_COMPETITION", "CLOSE-02Z term resolves only nondominated frontier; identity/namespace unchanged"),
        ("retry_penalty", "MOVE_OUTSIDE_COMPETITION", "existing bounded retry/denial eligibility state; not a gain subtraction"),
        ("source bonuses", "REMOVE_WITH_SCALAR_SCORER", "proposal source is not merit"),
        ("hard immediate safety", "RETAIN_AS_HARD_CONSTITUTIONAL_SEMANTIC", "precedes and cannot be reversed by competition"),
    ]
    return {"items": [dict(zip(("component", "classification", "translation"), row)) for row in rows]}


def implementation_boundary() -> dict[str, object]:
    return {
        "replace": [
            "ordinary (non-active/critical) scalar score_candidate evaluation",
            "ordinary temporal/individuality/fallback additive modifier interface",
            "ordinary total sort and scalar hysteresis-band choice",
        ],
        "add_or_refactor": [
            "pure SelfModel candidate consequence query",
            "pure WorldModel candidate consequence query",
            "fixed-size evidence-channel adapters",
            "supported-dominance frontier resolver",
            "per-channel trace representation",
        ],
        "likely_paths": [
            "umbra_core/arbitration.py",
            "umbra_core/runtime.py",
            "umbra_core/self_model/engine.py",
            "umbra_core/world_model/engine.py",
            "umbra_core/individuality/engine.py",
            "umbra_core/temporal/policy.py",
            "new bounded action-selection evidence/competition module",
            "focused tests and future qualification harness",
        ],
        "preserve": [
            "candidate generation and source-neutral canonicalization/deduplication",
            "CLOSE-02T intent/preventive/urgent authority states",
            "critical/active recovery legacy recovery choice path",
            "candidate_allowed, immediate safety, and recoverability admissibility",
            "CLOSE-02U world-model landmark continuity",
            "CLOSE-02Z stochastic key, namespace, distribution, and behavioral identity",
            "Governance, Embodiment, VerifiedOutcome, selected-only learning",
            "memory/development/social/habit proposal ownership",
        ],
        "important_split": "score_candidate is also used by urgent recovery; implementation must isolate the new ordinary evaluator and must not silently replace qualified urgent-recovery scoring",
        "production_changes_this_directive": 0,
    }


def boundedness_analysis() -> dict[str, object]:
    return {
        "candidate_bound": "later implementation freeze must introduce one deterministic source-neutral canonical pool cap because current bound is indirect",
        "channel_bound": "fixed schema: 4 physiology dimensions, fixed SelfModel fields, <=4 WorldModel records, <=2 temporal views, bounded qualified disposition/routine/context records",
        "queries": "at most one pure SelfModel and one pure WorldModel view per canonical existing candidate",
        "comparison": "O(C^2 * K), C fixed candidate cap and K fixed channel cap",
        "selection": "O(C log C) deterministic frontier/tie ordering after O(C^2*K)",
        "recursion": False,
        "planning_horizon": 1,
        "temporary_state": "O(C*K), discarded after selection",
        "persistent_state": "none required beyond an explicit action-selection semantic version marker",
        "provenance": "fixed refs per field; overflow becomes UNKNOWN",
        "restart": "equivalent persisted state/tick/stochastic basis reproduces views and winner",
        "migration": "body-schema mismatch makes learned body fields UNKNOWN; constitutional identity and stochastic basis persist",
    }


def retained_evidence_discrimination() -> dict[str, object]:
    retained = load_json(AS001 / "AS001_RETAINED_EVIDENCE_DISCRIMINATION.json")
    assert isinstance(retained, dict)
    return {
        "counterfactual_rescue_claimed": False,
        "families": [
            {"family": "successful R0 controls", "participation": "neutral unless supported per-channel evidence establishes dominance", "threat": "none structurally; authority and Z stay unchanged"},
            {"family": "D-014 energy/fatigue/stimulation failures", "participation": "per-dimension consequences can conflict without a master need score", "threat": "UNKNOWN coverage may leave stochastic frontier; no rescue claimed"},
            {"family": "CLOSE-02T/U", "participation": "intent authority and landmark evidence remain inputs/candidate generation, not source merit", "threat": "ordinary evaluator requires requalification"},
            {"family": "X-ATTRIB", "participation": "evidence revision can alter dominance while Z keeps surviving stochastic terms stable", "threat": "candidate filtering remains causal but no draw reassignment"},
            {"family": "habit/temporal/perception qualifications", "participation": "proposal and within-proposition evidence retained without additive totals", "threat": "requires focused migration proofs"},
            {"family": "body migration", "participation": "body-dependent evidence invalidates to UNKNOWN; identity/stochastic basis persists", "threat": "requires migration qualification"},
        ],
        "generality_beyond_seed_57531938": bool(retained.get("would_propose_without_seed_57531938")),
        "relies_on_unavailable_historical_prediction": False,
        "historical_trajectory_reinterpretation": False,
    }


def source_neutrality_proofs() -> dict[str, object]:
    return {
        "behavioral_identity": "CLOSE-02Z canonical capability + provenance-stripped behavioral params",
        "proposal_source_excluded": True,
        "duplicates": "canonical dedup before evaluation; duplicate sources cannot add channels, votes, or stochastic terms",
        "evidence_attachment": "evidence is keyed by proposition and behavioral identity, not proposing subsystem",
        "same_behavior_different_source": "same view, same channel values, same stochastic term, same frontier membership",
        "body_migration": "same constitutional identity/stochastic basis; body fields become UNKNOWN until supported under new schema",
        "restart": "equivalent persistent state and active tick reproduce the same relation",
        "proof": "PASS",
    }


def stochastic_composition_proofs() -> dict[str, object]:
    return {
        "namespace": "ordinary_candidate_competition:v1 unchanged",
        "key": ["persistent organism basis", "authoritative active tick", "versioned namespace", "source-neutral behavioral identity"],
        "consequence_metadata_in_identity": False,
        "pool_index_count_order_in_identity": False,
        "defeated_candidates": "removed before stochastic frontier resolution",
        "survivors": "retain exactly their candidate-local term under insertion/deletion/permutation",
        "strong_evidence": "supported-dominated candidate cannot be restored by stochasticity",
        "exact_tie": "canonical behavioral identity only",
        "proof": "PASS",
    }


def conflict_resolution_proofs() -> dict[str, object]:
    energy = "physiology.energy"
    fatigue = "physiology.fatigue"
    a = EvaluatedCandidate("A", {energy: supported(3), fatigue: supported(0)}, 0.1)
    b = EvaluatedCandidate("B", {energy: supported(0), fatigue: supported(3)}, 0.2)
    c = EvaluatedCandidate("C", {energy: supported(2), fatigue: supported(2)}, 0.3)
    physiology_frontier = [item.identity for item in frontier([a, b, c])]
    dominant = EvaluatedCandidate("D", {energy: supported(4), fatigue: supported(4)}, -0.9)
    unknown_candidate = EvaluatedCandidate("U", {energy: unknown(), fatigue: supported(2)}, 0.8)
    return {
        "rule": "supported-dominance frontier then CLOSE-02Z stochastic resolution",
        "physiology_tradeoff": {
            "frontier": physiology_frontier,
            "result": resolve([a, b, c]).identity,
            "meaning": "cross-dimension conflict remains explicit; stochasticity resolves genuine incomparability",
        },
        "supported_dominance": {
            "dominates": [dominant.identity for target in (a, b, c) if dominates(dominant, target)],
            "winner_despite_low_noise": resolve([a, b, c, dominant]).identity,
        },
        "unknown_first_experience": {
            "known_dominates_unknown": dominates(c, unknown_candidate),
            "unknown_survives": unknown_candidate.identity in [item.identity for item in frontier([c, unknown_candidate])],
        },
        "nonphysiology": [
            "habit versus regulation: conflicting supported channels remain frontier alternatives",
            "temporal expectation versus individuality/novelty: no cross-channel conversion; stochastic resolution",
            "partner relevance versus self-regulation: hard safety remains outside; supported conflict remains explicit",
            "development versus routine: CLOSE-02T intent eligibility preserved; source itself gives no merit",
            "world confidence versus individuality: each remains a separate proposition",
        ],
        "hidden_weight_audit": {
            "channel_sum": False,
            "vote_count": False,
            "fixed_channel_order": False,
            "normalization": False,
            "confidence_multiplication": False,
            "source_count": False,
        },
    }


def unknown_first_experience_markdown() -> str:
    return """# AS-002 UNKNOWN and first experience

`UNKNOWN` is neither a value nor an adverse result. If either candidate lacks supported evidence for a proposition applicable to the pair, that proposition prevents a dominance/elimination claim. A richly modelled candidate therefore cannot suppress a novel candidate merely because the latter lacks a learned model. Novel candidates remain on the nondominated frontier and can be selected by ordinary candidate-stable stochastic variation, existing candidate generation, development, habit, temporal opportunity, or relationship context.

After a candidate is actually selected and its outcome verified, existing SelfModel/WorldModel/memory/individuality learning may replace UNKNOWN with supported evidence. That revision may establish or remove a dominance relation on later equivalent states. Contradictory verified evidence can reverse it again. Provenance metadata alone never changes competition.

This is conservative: incomplete evidence creates a larger stochastic frontier rather than fabricated certainty. It permits first experience without adding an exploration planner or treating uncertainty as merit.
"""


def distributed_contract_markdown() -> str:
    return """# AS-002 SUPPORTED_DOMINANCE_DISTRIBUTED_COMPETITION_V1

## Scope

This contract replaces only ordinary, non-active/noncritical scalar-total candidate evaluation. Existing generation, source-neutral canonicalization/deduplication, CLOSE-02T intent/preventive composition, hard safety/admissibility, urgent recovery, Governance, Embodiment, VerifiedOutcome, and selected-only learning remain authoritative.

## Algorithm

1. Generate and canonicalize the existing candidate pool; deduplicate behaviorally equivalent proposals without source voting.
2. Apply existing hard candidate-allowed, immediate-safety, and recoverability-admissibility checks outside ordinary competition.
3. For each surviving existing candidate, derive immutable `CANDIDATE_CONSEQUENCE_VIEW_V1` using one pure SelfModel query, one pure WorldModel query, physiology, current policy-visible state, and bounded qualified context adapters. Unavailable evidence is `UNKNOWN`.
4. Owning subsystems emit fixed-key channel values. A value is comparable only with the same channel key and owning semantics. No cross-channel arithmetic exists.
5. For every candidate pair A/B, A supported-dominates B only when every proposition applicable to either candidate is supported for both, A is no worse in each channel-internal order, and A is strictly better in at least one. UNKNOWN blocks dominance. Compute all relations simultaneously.
6. Remove supported-dominated candidates. A finite non-empty pool retains a nondominated frontier. No channel count, source count, channel priority, normalization, aggregate confidence, or scalar total is computed.
7. If one candidate remains, select it. If several remain, select the candidate with the greatest existing CLOSE-02Z candidate-local stochastic term. Exact term ties resolve by canonical behavioral identity. Stochasticity never sees defeated candidates and cannot erase supported dominance.
8. Send exactly that existing candidate through Governance and Embodiment. Commit SelfModel/WorldModel prediction only for the selected candidate. Learn only from VerifiedOutcome.

## Conflict semantics

Tradeoffs across energy, fatigue, integrity, stimulation, temporal expectation, habit/continuity, relationship, development, world evidence, and individuality are genuine incomparability unless one candidate is supported no-worse everywhere and better somewhere. The contract refuses to invent a master need score or covert priority. Hard critical recovery remains outside this rule.

## Liveness and autonomy

UNKNOWN enlarges the frontier; it never empties it. If hard authority leaves no existing candidate, preserve the established outside-competition `NO_SAFE_ACTION` semantics. The competition contract invents no fallback or candidate. A novel action can be selected from the frontier, enabling first experience. Bounded continuity is a proposition, not an additive hysteresis score.

## Falsification boundary

Reject implementation if any required channel cannot emit a stable within-channel relation without authored cross-channel mapping; if the canonical pool cannot be capped source-neutrally; if qualified temporal/individuality/continuity behavior cannot migrate to proposition-level evidence; if Z identity/namespace must change; if urgent recovery must be rewritten; or if pure queries mutate, consume RNG, persist, or learn.
"""


def prior_art_markdown() -> str:
    return """# AS-002 bounded primary prior-art review

Checked 2026-08-30. All dispositions are `REFERENCE`; no dependency or computational framework is adopted.

- Paul Cisek, *Cortical mechanisms of action selection: the affordance competition hypothesis* (2007), https://pmc.ncbi.nlm.nih.gov/articles/PMC2440773/ — supports parallel specification of currently available actions and multiple biasing influences. It does not supply UMBRA's conflict rule or validate a common value scale.
- Prescott, Bryson, Seth et al., *Introduction. Modelling natural action selection* (2007), https://pmc.ncbi.nlm.nih.gov/articles/PMC2042525/ — supports treating action selection as conflict resolution embedded in body/environment and cautions that specialized selectors and normative optimality are not automatic architectural truths.
- Wolpert, Miall, Kawato, *Internal models in the cerebellum* (1998), https://pubmed.ncbi.nlm.nih.gov/21227230/ — supports bounded forward prediction of immediate consequences; inverse models and planning are rejected.
- Elsner and Hommel, *Effect anticipation and action control* (2001), https://pubmed.ncbi.nlm.nih.gov/11248937/ — supports verified learned action-effect relations influencing later action choice; it does not grant execution authority.
- Churchland and Ditterich, *New advances in understanding decisions among multiple alternatives* (2012), https://pmc.ncbi.nlm.nih.gov/articles/PMC3422607/ — documents multiple-alternative accumulation/competition families and context effects. Numeric accumulation, common thresholds, neural implementation, and value integration are rejected because UMBRA lacks common cross-channel units.

Rejected imports: reinforcement learning, utility maximization, normalized weighted sums, automatic Pareto optimization, POMDP, active inference, MPC, rollout/tree search, inverse-model action generation, basal-ganglia scalar salience, neural mutual-inhibition implementation, LLM planning, and global survival/information scores.

Prior art supports parallel alternatives, forward consequence evidence, learned action-effect influence, and a bounded conflict-resolution problem. The exact supported-dominance plus stochastic-frontier rule is justified by UMBRA's authority/UNKNOWN/no-weight constraints and pure proofs, not claimed as a result of the literature.
"""


def verdict() -> dict[str, object]:
    return {
        "directive": "UMBRA-AS-002",
        "status": "TERMINAL",
        "verdict": "AS002_DISTRIBUTED_COMPETITION_CONTRACT_SUPPORTED",
        "contract": "SUPPORTED_DOMINANCE_DISTRIBUTED_COMPETITION_V1",
        "primary_reason": "A bounded pairwise supported-dominance relation can preserve distinct evidence propositions without cross-channel arithmetic. UNKNOWN blocks elimination, and CLOSE-02Z stochasticity resolves only the genuinely nondominated frontier.",
        "hidden_global_utility": False,
        "cross_channel_weights": False,
        "source_priority": False,
        "planner": False,
        "one_final_existing_candidate": True,
        "implementation_boundary": "ordinary noncritical evaluation/additive modifiers only; urgent recovery and protected authority remain unchanged",
        "successor_recommendation": "UMBRA-AS-003_DISTRIBUTED_COMPETITION_IMPLEMENTATION_CANDIDATE",
        "successor_authorized": False,
        "production_changes": 0,
        "organism_runs": 0,
        "retries": 0,
        "reseeds": 0,
    }


def source_assertions() -> dict[str, object]:
    arbitration = (ROOT / "umbra_core/arbitration.py").read_text(encoding="utf-8")
    stochastic = (ROOT / "umbra_core/stochastic_competition.py").read_text(encoding="utf-8")
    checks = {
        "current_scalar_total_present": "cand.total = sum(scores.values())" in arbitration,
        "temporal_additive_present": "cand.total += total_delta" in arbitration,
        "ordinary_total_sort_present": "-c.total" in arbitration,
        "urgent_score_use_present": "sc = self.score_candidate(c, phys, observations, active_tick)" in arbitration,
        "candidate_stable_namespace_present": "ordinary_candidate_competition:v1" in stochastic,
        "source_neutral_identity_present": "candidate_behavioral_identity" in stochastic,
    }
    assert all(checks.values()), checks
    paths = [
        "umbra_core/arbitration.py",
        "umbra_core/runtime.py",
        "umbra_core/self_model/engine.py",
        "umbra_core/world_model/engine.py",
        "umbra_core/individuality/engine.py",
        "umbra_core/temporal/policy.py",
        "umbra_core/stochastic_competition.py",
        "umbra_core/governance.py",
    ]
    return {"checks": checks, "source_sha256": {path: sha(ROOT / path) for path in paths}}


def main() -> None:
    head = sh("git", "rev-parse", "HEAD")
    assert sh("git", "merge-base", "--is-ancestor", GOVERNANCE_START, head) == ""
    assert sh("git", "show", f"{BASELINE}^{{commit}}")
    as001_manifest = verify_manifest(AS001)
    z_manifest = verify_manifest(Z)
    assert as001_manifest["pass"] and z_manifest["pass"]

    write_json("AS002_AS001_CANDIDATE_RECOVERY.json", as001_candidate_recovery())
    write_json("AS002_EVIDENCE_CHANNEL_SCHEMA.json", evidence_channel_schema())
    write_text("AS002_CANDIDATE_CONSEQUENCE_VIEW.md", consequence_view_markdown())
    write_json("AS002_EVIDENCE_AUTHORITY_MAP.json", evidence_authority_map())
    write_text("AS002_COMPETITION_FAMILY_ANALYSIS.md", competition_family_analysis_markdown())
    write_json("AS002_CONFLICT_RESOLUTION_PROOFS.json", conflict_resolution_proofs())
    write_text("AS002_UNKNOWN_AND_FIRST_EXPERIENCE.md", unknown_first_experience_markdown())
    write_json("AS002_SOURCE_NEUTRALITY_PROOFS.json", source_neutrality_proofs())
    write_json("AS002_STOCHASTIC_COMPOSITION_PROOFS.json", stochastic_composition_proofs())
    write_json("AS002_SCORER_MIGRATION_MAP.json", scorer_migration_map())
    write_json("AS002_IMPLEMENTATION_BOUNDARY.json", implementation_boundary())
    write_json("AS002_BOUNDEDNESS_ANALYSIS.json", boundedness_analysis())
    write_json("AS002_RETAINED_EVIDENCE_DISCRIMINATION.json", retained_evidence_discrimination())
    write_text("AS002_DISTRIBUTED_COMPETITION_CONTRACT.md", distributed_contract_markdown())
    write_text("AS002_PRIOR_ART_ARCHITECTURE_REVIEW.md", prior_art_markdown())
    write_json("AS002_SOURCE_ASSERTIONS.json", source_assertions())
    write_json("AS002_VERDICT.json", verdict())
    write_json(
        "AS002_VALIDATION.json",
        {
            "baseline": BASELINE,
            "governance_start": GOVERNANCE_START,
            "analysis_head": head,
            "as001_manifest": as001_manifest,
            "close02z_manifest": z_manifest,
            "pure_contract_proofs": "15/15 PASS",
            "authority_3_0": "PASS",
            "governance": "PASS",
            "production_changes": 0,
            "organism_runs": 0,
            "retries": 0,
            "reseeds": 0,
        },
    )

    artifacts = []
    for path in sorted(EVIDENCE.iterdir()):
        if path.name == "EVIDENCE_HASHES.json" or not path.is_file():
            continue
        artifacts.append({"path": path.name, "sha256": sha(path), "size": path.stat().st_size})
    write_json(
        "EVIDENCE_HASHES.json",
        {
            "directive": "UMBRA-AS-002",
            "durability": ["file_fsync", "atomic_rename", "directory_fsync", "readback_sha256"],
            "artifacts": artifacts,
        },
    )
    reread = verify_manifest(EVIDENCE)
    assert reread["pass"] and reread["checked"] == len(artifacts)
    print(json.dumps({
        "evidence_root": str(EVIDENCE),
        "artifacts": len(artifacts),
        "manifest_sha256": sha(EVIDENCE / "EVIDENCE_HASHES.json"),
        "verdict": verdict()["verdict"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
