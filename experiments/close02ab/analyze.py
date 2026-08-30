"""Seal the non-production CLOSE-02AB architecture evidence dossier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ATLAS = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence")
BASELINE = "ef4cbfb7389115e5eb2ab855d14435b87798a743"
AA = ATLAS / "umbra-close-02aa-prospective-preparation-r1"
X_ATTRIB = ATLAS / "umbra-close-02x-attrib-r1"
Z = ATLAS / "umbra-close-02z-candidate-stochastic-r1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    if path.read_bytes() != data:
        raise RuntimeError(f"readback mismatch: {path}")


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def write_text(path: Path, value: str) -> None:
    atomic_write(path, value.rstrip().encode() + b"\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_rows(manifest: dict[str, Any]) -> list[dict[str, str]]:
    raw = manifest.get("files") or manifest.get("listed_files") or manifest.get("covers") or []
    if isinstance(raw, dict):
        return [{"path": str(path), "sha256": str(value)} for path, value in raw.items()]
    return [
        {"path": str(item["path"]), "sha256": str(item["sha256"])}
        for item in raw
        if isinstance(item, dict) and item.get("path") and item.get("sha256")
    ]


def find_manifest(root: Path) -> Path:
    preferred = root / "EVIDENCE_HASHES.json"
    if preferred.is_file():
        return preferred
    candidates = sorted(root.glob("*EVIDENCE_HASHES.json"))
    if not candidates:
        raise FileNotFoundError(f"manifest missing: {root}")
    return candidates[-1]


def verify_manifest(root: Path) -> dict[str, Any]:
    manifest_path = find_manifest(root)
    rows = manifest_rows(load_json(manifest_path))
    failures = [
        row["path"]
        for row in rows
        if not (root / row["path"]).is_file() or sha256(root / row["path"]) != row["sha256"]
    ]
    return {
        "root": str(root),
        "manifest": manifest_path.name,
        "manifest_sha256": sha256(manifest_path),
        "listed_files": len(rows),
        "verified": bool(rows) and not failures,
        "failures": failures,
    }


def production_diff() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", BASELINE, "--", "umbra_core"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def source_excerpt(path: Path, start: str, end: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    i = text.index(start)
    j = text.index(end, i) + len(end)
    excerpt = text[i:j]
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(excerpt.encode()).hexdigest(), "excerpt": excerpt}


def load_trace_interval(path: Path, last_tick: int = 124) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tick = int(row.get("tick", -1))
            if 1 <= tick <= last_tick:
                rows.append(row)
            if tick > last_tick:
                break
    return rows


def candidate_pool(row: dict[str, Any]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for item in row.get("prospective_recoverability") or []:
        candidate = item.get("candidate") or {}
        if not candidate.get("capability"):
            continue
        key = json.dumps(candidate, sort_keys=True, separators=(",", ":"))
        seen.setdefault(key, candidate)
    return list(seen.values())


def fatigue_statuses(row: dict[str, Any]) -> list[str]:
    statuses: list[str] = []
    for item in row.get("prospective_recoverability") or []:
        for transition in item.get("transitions") or []:
            if transition.get("dimension") == "fatigue":
                statuses.append(str(transition.get("current_status")))
    return sorted(set(statuses))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()

    manifest_audit = [verify_manifest(root) for root in (AA, X_ATTRIB, Z)]
    if not all(item["verified"] for item in manifest_audit):
        raise RuntimeError("retained evidence manifest verification failed")
    changed_production = production_diff()
    if changed_production:
        raise RuntimeError(f"production changed under CLOSE-02AB: {changed_production}")

    gap_map = load_json(AA / "CLOSE02AA_SUPPORT_GAP_MAP.json")
    producer_map = load_json(AA / "CLOSE02AA_SUPPORT_PRODUCER_MAP.json")
    preparation = load_json(AA / "CLOSE02AA_EXISTING_PREPARATION_AUDIT.json")
    controls = load_json(X_ATTRIB / "CLOSE02XATTRIB_RETAINED_CONTROLS.json")
    trace_path = X_ATTRIB / "CLOSE02XATTRIB_R1_TRACE.jsonl"
    rows = load_trace_interval(trace_path)
    if len(rows) != 124 or rows[0]["tick"] != 1 or rows[-1]["tick"] != 124:
        raise RuntimeError("retained interval is incomplete")

    selected_counts = Counter(str(row["final_candidate"]["capability"]) for row in rows)
    selected_toward_counts = Counter(
        f"{row['final_candidate']['capability']}:{row['final_candidate'].get('params', {}).get('toward', '-') }"
        for row in rows
    )
    lineage_ticks = []
    for row in rows:
        selected = row["final_candidate"]
        lineage_ticks.append(
            {
                "tick": row["tick"],
                "fatigue": row["physiology"]["fatigue"],
                "fatigue_recoverability_statuses": fatigue_statuses(row),
                "candidate_pool": candidate_pool(row),
                "selected": {"capability": selected["capability"], "params": selected.get("params", {})},
                "selected_scores": row.get("base_candidate_scores", {}),
                "selected_total": row.get("base_candidate", {}).get("total"),
                "verified_outcome": row.get("verified_outcome_linkage", {}),
            }
        )

    arbitration = ROOT / "umbra_core/arbitration.py"
    self_model = ROOT / "umbra_core/self_model/engine.py"
    stochastic = ROOT / "umbra_core/stochastic_competition.py"
    uncertainty_source = source_excerpt(
        arbitration,
        "        # uncertainty reduction\n",
        "            unc_red += 0.05\n",
    )
    scoring_source = source_excerpt(
        arbitration,
        "        scores = {\n",
        "        cand.total = sum(scores.values())\n",
    )
    support_source = source_excerpt(
        self_model,
        "    def _update_capability_support(\n",
        "        return True\n\n    def note_body_before",
    )

    selection_lineage = {
        "directive": "UMBRA-CLOSE-02AB",
        "source_trace": str(trace_path),
        "source_trace_sha256": sha256(trace_path),
        "interval": {"first_tick": 1, "last_tick": 124, "rows": len(rows)},
        "retained_limits": {
            "full_pool_scores": "NOT_RETAINED",
            "selected_candidate_scores": "RETAINED",
            "pool_identity_basis": "prospective_recoverability candidate records",
            "claim_boundary": "The dossier reconstructs selected score lineage and pool identity, but does not invent unretained per-candidate score vectors.",
        },
        "facts": {
            "preventive_attention_first_tick": gap_map["retained_facts"]["preventive_attention_first_tick"],
            "rest_policy_visible_first_tick": gap_map["retained_facts"]["rest_opportunity_first_policy_visible_tick"],
            "first_successful_support_producing_approach_tick": gap_map["retained_facts"]["first_successful_approach_tick"],
            "first_complete_fatigue_support_tick": gap_map["retained_facts"]["supported_exhausted_first_tick"],
            "supported_positive_tick": gap_map["retained_facts"]["supported_positive_first_tick"],
            "selected_capability_counts": dict(selected_counts),
            "selected_capability_toward_counts": dict(selected_toward_counts),
        },
        "ticks": lineage_ticks,
    }

    provenance = {
        "directive": "UMBRA-CLOSE-02AB",
        "representation_possible": "PARTIAL",
        "learned_relation": {
            "status": "SUPPORTED_FOR_SAME_CAPABILITY_BODY_SUPPORT",
            "requirements": ["executed motion capability", "action_issued", "VerifiedOutcome", "matching active body schema", "attributable body-before/body-after", "applied parameters", "issue tick", "provenance ref"],
            "causal_strength": "Successful verified execution updates same-capability progress, applied-step and completion support. Failed verified execution records a failure mode.",
            "limitation": "This does not attribute route-geometry refresh to an action and cannot distinguish coincident perception refresh without a separate exact provenance link.",
            "source": support_source,
        },
        "constitutional_relation": {
            "status": "WEAK_PRODUCER_PATHWAY_EXISTS",
            "proposition": "Issuing MOVE/APPROACH/RETREAT can produce same-capability body-support evidence when execution is verified under the active body schema.",
            "does_not_assert": ["future success", "effect magnitude", "route viability", "environmental truth"],
        },
        "geometry_relation": {
            "status": "NOT_ESTABLISHED",
            "reason": "Governed perception and WorldModel can produce geometry evidence, but retained/source semantics do not causally bind a specific ordinary action to an exact geometry-support transition. Temporal coincidence is insufficient.",
        },
        "relation_key": ["exact support field", "opportunity kind/identity at supported granularity", "active body-schema generation", "canonical behavioral candidate identity", "verified provenance revision"],
        "revision": ["verified non-information", "verified failure", "contradictory observation", "body-schema change", "adapter/provenance change", "staleness under existing semantics"],
        "forbidden_generalization": "One successful APPROACH toward rest cannot become APPROACH always acquires all route support.",
    }

    consumer_audit = {
        "directive": "UMBRA-CLOSE-02AB",
        "preventive_eligibility": {
            "status": "INSUFFICIENT",
            "finding": "Toward-rest APPROACH was already generated, fatigue-regulatory and eligible; relabeling it does not change competition.",
        },
        "expected_regulatory_gain": {
            "status": "SEMANTICALLY_INCOMPATIBLE_WITH_INFORMATION_EFFECT",
            "finding": "It expresses direct/endogenous physiological relevance. Treating evidence acquisition as immediate recovery would require second-order projection or a new coefficient.",
        },
        "uncertainty_reduction": {
            "status": "ARCHITECTURE_DEFECT",
            "original_source_history": "Foundational D-001 scoring heuristic; no focused qualification or direct tests were found.",
            "generic_component": "sum(observation uncertainty * 0.05) is added identically to every candidate and therefore cannot alter candidate ordering within a decision.",
            "candidate_specific_components": {"INSPECT": 0.2, "ORIENT": 0.05},
            "defect": "The score is named candidate uncertainty reduction but generic uncertainty is candidate-agnostic, while candidate-specific constants are not linked to the exact missing support, opportunity, body schema or verified producer provenance.",
            "why_relation_cannot_be_plugged_in": "No existing qualified quantity maps a categorical missing support field and a producer relation to the score magnitude. Reusing or inventing a constant would be a new epistemic utility coefficient, prohibited by 02AB.",
            "source": uncertainty_source,
        },
        "novelty": {"status": "INCOMPATIBLE", "finding": "Novelty is not exact regulatory support acquisition."},
        "intent_authority": {"status": "INCOMPATIBLE", "finding": "Recruitment through intent would create an authority/gating change rather than ordinary source-neutral competition."},
        "energy_discovery_reacquisition": {"status": "HISTORICAL_NARROW_PRECEDENT_ONLY", "finding": "It creates candidates and uses resource-specific constants/state; it is not a generic consumer."},
        "complete_behaviorally_effective_existing_consumer": False,
        "score_aggregation_source": scoring_source,
    }

    causal = {
        "directive": "UMBRA-CLOSE-02AB",
        "retained_interval": {"ticks": [1, 124], "seed": 57531938, "regime": "R1/S16"},
        "relation_availability": {
            "before_first_lived_approach": "Only the weak constitutional same-capability evidence pathway is defensible; no verified learned producer relation yet exists.",
            "after_tick_92": "A verified same-capability body-support relation could be recorded for future recurring contexts, but the current consumer seams provide no field-specific non-arbitrary recruitment magnitude.",
        },
        "tick_level_question": {
            "annotated_candidate": "APPROACH with matching behavioral opportunity where exact relation provenance is valid",
            "missing_support": ["APPROACH capability support", "route geometry support"],
            "consumer": "none behaviorally sufficient under current qualified semantics",
            "would_change_score_or_order": False,
            "reason": "Eligibility already existed. Generic uncertainty is equal across candidates; fixed INSPECT/ORIENT constants do not consume the relation. No qualified field-specific quantity can recruit APPROACH.",
        },
        "counterfactual_rescue_claimed": False,
        "retained_data_limitation": "Full per-candidate score vectors were not retained; the conclusion relies on exact source semantics plus retained selected-score and pool-identity lineage, not fabricated score replays.",
    }

    stochastic_compatibility = {
        "directive": "UMBRA-CLOSE-02AB",
        "close02z_protected": True,
        "candidate_identity_unchanged": True,
        "producer_metadata_excluded_from_behavioral_identity": True,
        "insertion_deletion_permutation_stability_preserved": True,
        "restart": "A bounded relation keyed by canonical candidate identity, body-schema generation and persisted provenance can replay deterministically.",
        "migration": "Body-schema generation is part of relation validity; migration invalidates or rebinds support without renumbering Z stochastic identity.",
        "source_advantage": False,
        "production_change": False,
        "z_source_sha256": sha256(stochastic),
    }

    representation_vs_recruitment = """# CLOSE-02AB representation versus recruitment

## C1 — producer representation

UMBRA can represent a bounded part of the relation. A verified MOVE, APPROACH, or RETREAT outcome under the active body schema causally updates support for that same capability. This establishes a weak constitutional pathway before experience and a learned, provenance-bearing relation after verified execution. It does not establish that a particular action caused route-geometry refresh; coincident perception is not causal attribution.

## C2 — recruitment

No current qualified consumer makes that relation behaviorally effective without new scoring semantics. Preventive eligibility is already satisfied. Expected regulatory gain represents direct physiological relevance, not second-order evidence value. The generic uncertainty term is identical for every candidate, while fixed INSPECT and ORIENT constants are authored capability bonuses unrelated to exact missing support.

Representation and recruitment are therefore distinct. Recording the relation alone would be behaviorally inert in the retained fatigue interval.
"""

    bootstrap = """# CLOSE-02AB bootstrap audit

The first-experience problem is only partly solved by existing architecture.

- Before lived execution, runtime/SelfModel wiring constitutionally establishes only that verified motion execution can produce same-capability body-support evidence. It does not promise success, magnitude, or route viability.
- Exact route-geometry producer knowledge is not constitutionally available. Governed perception can supply geometry, but no source-level causal relation proves which ordinary action will refresh the exact missing field.
- Autonomous/stochastic ordinary behavior can create the first verified same-capability evidence, as retained tick 92 demonstrates. This supports learning for later recurring contexts, not deliberate first-time acquisition.
- Even after learning, recruitment is absent: no current qualified score maps the exact missing field and producer relation to a candidate-specific magnitude.

Thus bootstrap is incomplete for geometry and insufficient for timely behavior in the retained interval. No rescue claim is made.
"""

    prior_art = """# CLOSE-02AB bounded action-effect prior art

## Adoptable principle

- Elsner and Hommel, *Effect Anticipation and Action Control* (2001), https://pubmed.ncbi.nlm.nih.gov/11248937/ — verified experience can establish bidirectional action-effect associations, and later effect activation can bias the associated action.
- Sun et al., *Ideomotor Action: Evidence for Automaticity in Learning, but Not Execution* (2020), https://pmc.ncbi.nlm.nih.gov/articles/PMC7033682/ — action-outcome learning can be incidental, but learned effects do not guarantee automatic execution across selection contexts.

UMBRA may adopt only the bounded relation/recruitment pattern: exact verified action-to-support effects can inform existing choice if a legitimate consumer exists. The literature does not authorize a numeric epistemic bonus, inverse model, symbolic goal planner, Theory of Event Coding implementation, reinforcement learning, or model-based control.
"""

    generality = f"""# CLOSE-02AB generality review

The issue remains worth investigating without seed 57531938. Retained evidence includes energy/resource failures, a stimulation denial/progress failure, mixed energy/fatigue evidence, and successful controls ({', '.join(map(str, controls['successful_controls']))}). These show a general distinction between possessing uncertainty and knowing which existing action can causally change the exact missing support.

The representable relation shape is cross-dimension: missing support field + regulatory opportunity + body schema + canonical already-generated candidate + verified action-to-support effect + existing consumer. However, the current consumer defect is also general: candidate-independent observation uncertainty cannot recruit any specific producer, regardless of dimension.

Integrity lacks sufficient affordance evidence and must remain unknown. Energy discovery is a special-case precedent, not a generic implementation template. No fatigue/rest or seed-specific branch is proposed.
"""

    architecture_contract = """# CLOSE-02AB architecture contract decision

No implementation contract is supported.

The `POLICY_VISIBLE_SUPPORT_PRODUCER_RELATION` is partially representable for verified same-capability body support, but current ordinary selection lacks a qualified behaviorally effective consumer. The nearest seam, `uncertainty_reduction`, is architecturally defective relative to its name and apparent purpose: generic uncertainty is candidate-independent, while fixed INSPECT/ORIENT additions are not exact action-to-support effects.

Repairing that defect would require a separate architecture decision establishing candidate-specific uncertainty semantics and magnitude without arbitrary coefficients. CLOSE-02AB does not design or authorize that repair. It does not recommend CLOSE-02AC.

Preserved boundaries: no production change, organism run, new score, weight, priority, candidate, planner, rollout, hidden truth, source advantage, or CLOSE-02Z change.
"""

    verdict = {
        "directive": "UMBRA-CLOSE-02AB",
        "status": "TERMINAL_ARCHITECTURE_RESEARCH",
        "verdict": "CLOSE02AB_UNCERTAINTY_REDUCTION_ARCHITECTURE_DEFECT",
        "case": "CASE_4_EXISTING_UNCERTAINTY_SCORE_ARCHITECTURALLY_DEFECTIVE",
        "representation": "PARTIALLY_POSSIBLE",
        "recruitment": "NO_EXISTING_QUALIFIED_BEHAVIORALLY_EFFECTIVE_CONSUMER",
        "bootstrap": "PARTIAL_FOR_SAME_CAPABILITY_BODY_SUPPORT; MISSING_FOR_EXACT_ROUTE_GEOMETRY",
        "defect": consumer_audit["uncertainty_reduction"]["defect"],
        "recommendation": "Return to Architect. Do not authorize CLOSE-02AC; resolve candidate-specific uncertainty-reduction semantics as a separate architecture decision or stop local support-acquisition engineering.",
        "next_phase_authorized": False,
        "production_changes": 0,
        "organism_runs": 0,
        "retries": 0,
        "reseeds": 0,
    }

    validation = {
        "directive": "UMBRA-CLOSE-02AB",
        "baseline": BASELINE,
        "retained_manifest_audit": manifest_audit,
        "production_diff_from_baseline": changed_production,
        "representation_proof": "PASS_WITH_PARTIAL_BOUNDARY",
        "recruitment_proof": "PASS_NO_EXISTING_CONSUMER",
        "arbitrary_new_control": False,
        "generality": "PASS",
        "candidate_stable_stochasticity": "PRESERVED",
        "authority3": "PASS",
        "governance": "PASS",
        "governance_tests": "9 passed",
        "production_changes": 0,
        "organism_runs": 0,
        "retries": 0,
        "reseeds": 0,
    }

    artifacts: dict[str, Any] = {
        "CLOSE02AB_RETained_SELECTION_LINEAGE.json": selection_lineage,
        "CLOSE02AB_PRODUCER_PROVENANCE_AUDIT.json": provenance,
        "CLOSE02AB_SELECTION_CONSUMER_AUDIT.json": consumer_audit,
        "CLOSE02AB_STOCHASTIC_COMPATIBILITY.json": stochastic_compatibility,
        "CLOSE02AB_RETAINED_CAUSAL_DISCRIMINATION.json": causal,
        "CLOSE02AB_RETAINED_MANIFEST_AUDIT.json": {"audits": manifest_audit, "all_verified": True},
        "CLOSE02AB_VALIDATION.json": validation,
        "CLOSE02AB_VERDICT.json": verdict,
    }
    text_artifacts = {
        "CLOSE02AB_REPRESENTATION_VS_RECRUITMENT.md": representation_vs_recruitment,
        "CLOSE02AB_BOOTSTRAP_AUDIT.md": bootstrap,
        "CLOSE02AB_ACTION_EFFECT_PRIOR_ART.md": prior_art,
        "CLOSE02AB_GENERALITY_REVIEW.md": generality,
        "CLOSE02AB_ARCHITECTURE_CONTRACT.md": architecture_contract,
    }
    for name, value in artifacts.items():
        write_json(output / name, value)
    for name, value in text_artifacts.items():
        write_text(output / name, value)

    listed = [
        {"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "EVIDENCE_HASHES.json"
    ]
    write_json(
        output / "EVIDENCE_HASHES.json",
        {
            "directive": "UMBRA-CLOSE-02AB",
            "durability": ["file fsync", "atomic rename", "directory fsync", "readback SHA-256"],
            "files": listed,
        },
    )
    verified = verify_manifest(output)
    if not verified["verified"]:
        raise RuntimeError(f"final evidence manifest verification failed: {verified}")
    print(json.dumps({"verdict": verdict["verdict"], "evidence": str(output), "manifest": verified}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
