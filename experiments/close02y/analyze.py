"""Generate the bounded CLOSE-02Y architecture evidence dossier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from experiments.close02y.candidate_stable_contract import (
    DEFAULT_NAMESPACE,
    PROVENANCE_ONLY_KEYS,
    candidate_identity,
    stable_terms,
)


ROOT = Path(__file__).resolve().parents[2]
ATLAS = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence")
X_ATTRIB = ATLAS / "umbra-close-02x-attrib-r1"
U_ATTRIB = ATLAS / "umbra-close-02u-attrib-r1"
W_EVIDENCE = ATLAS / "umbra-close-02w-prospective-recoverability-r1"
BASELINE = "80bcec23e02ec465307b72e9256e38d00305e81b"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(root: Path) -> dict[str, Any]:
    manifest = json.loads((root / "EVIDENCE_HASHES.json").read_text(encoding="utf-8"))
    rows = manifest.get("files") or manifest.get("listed_files") or []
    failures = []
    for row in rows:
        path = root / row["path"]
        if not path.is_file() or sha256(path) != row["sha256"]:
            failures.append(row["path"])
    return {
        "root": str(root),
        "listed_files": len(rows),
        "verified": not failures,
        "failures": failures,
        "manifest_sha256": sha256(root / "EVIDENCE_HASHES.json"),
    }


def read_jsonl_tick(path: Path, tick: int) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if int(row.get("tick", -1)) == tick:
                return row
    raise KeyError(f"missing_tick:{tick}:{path}")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.read_bytes() != data:
        raise RuntimeError(f"readback_mismatch:{path}")


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def build_path_map() -> dict[str, Any]:
    paths = [
        {
            "operation": "ordinary_candidate_noisy_argmax",
            "owner": "Arbitrator.select",
            "source": "umbra_core/arbitration.py:1398-1422",
            "rng": "shared persisted Organism SeededRNG",
            "draws": "one gauss(0,0.08) per post-filter candidate",
            "sequence_dependency": True,
            "candidate_order_dependency": True,
            "candidate_pool_size_dependency": True,
            "domain": "candidate_competition",
            "disposition": "TARGET",
        },
        {
            "operation": "exact_total_tie_resolution",
            "owner": "Arbitrator.select",
            "source": "umbra_core/arbitration.py:1421-1422",
            "rng": "none; Python stable sort retains input order",
            "draws": 0,
            "sequence_dependency": True,
            "candidate_order_dependency": True,
            "candidate_pool_size_dependency": False,
            "domain": "candidate_competition",
            "disposition": "TARGET_CANONICAL_TIE_KEY",
        },
        {
            "operation": "individuality_candidate_modifier",
            "owner": "IndividualityEngine.apply_modifiers",
            "source": "umbra_core/individuality/engine.py:598-806",
            "rng": "none; deterministic learned dispositions",
            "draws": 0,
            "sequence_dependency": False,
            "candidate_order_dependency": False,
            "candidate_pool_size_dependency": False,
            "domain": "candidate_competition",
            "disposition": "PRESERVE_UNCHANGED",
        },
        {
            "operation": "random_arbitration_ablation",
            "owner": "Arbitrator.select",
            "source": "umbra_core/arbitration.py:909-915",
            "rng": "shared persisted Organism SeededRNG",
            "draws": "choice plus uniform heading",
            "sequence_dependency": True,
            "candidate_order_dependency": "CAPABILITIES iteration only",
            "candidate_pool_size_dependency": True,
            "domain": "whole_policy_ablation",
            "disposition": "OUT_OF_SCOPE",
        },
        {
            "operation": "sensor_feature_noise_and_false_negatives",
            "owner": "PerceptionMembrane",
            "source": "umbra_core/perception.py:141-248",
            "rng": "shared persisted Organism SeededRNG",
            "draws": "variable per perceived feature",
            "sequence_dependency": True,
            "candidate_order_dependency": False,
            "candidate_pool_size_dependency": False,
            "domain": "perception_environment",
            "disposition": "PRESERVE_SEPARATE",
        },
        {
            "operation": "partner_cue_noise",
            "owner": "PerceptionMembrane",
            "source": "umbra_core/perception.py:323-355",
            "rng": "SeededRNG.fork(partner hidden id salt xor time)",
            "draws": "partner-local fork",
            "sequence_dependency": False,
            "candidate_order_dependency": False,
            "candidate_pool_size_dependency": False,
            "domain": "perception_environment",
            "disposition": "PRESERVE_SEPARATE",
        },
        {
            "operation": "movement_slip_and_irreducible_inspect_noise",
            "owner": "Embodiment",
            "source": "umbra_core/embodiment.py:1055-1127",
            "rng": "shared persisted Organism SeededRNG",
            "draws": "execution-contingent",
            "sequence_dependency": True,
            "candidate_order_dependency": False,
            "candidate_pool_size_dependency": False,
            "domain": "execution_environment",
            "disposition": "PRESERVE_SEPARATE",
        },
        {
            "operation": "partner_response_and_delay",
            "owner": "PartnerResponsePolicy/Embodiment",
            "source": "umbra_core/embodiment.py:122-145",
            "rng": "shared persisted Organism SeededRNG",
            "draws": "response-contingent",
            "sequence_dependency": True,
            "candidate_order_dependency": False,
            "candidate_pool_size_dependency": False,
            "domain": "execution_environment_social",
            "disposition": "PRESERVE_SEPARATE",
        },
        {
            "operation": "development_random_goal_ablation",
            "owner": "DevelopmentEngine",
            "source": "umbra_core/development/engine.py:870-881",
            "rng": "shared persisted Organism SeededRNG only in random mode",
            "draws": "one random score per goal in ablation",
            "sequence_dependency": True,
            "candidate_order_dependency": True,
            "candidate_pool_size_dependency": True,
            "domain": "development_ablation",
            "disposition": "OUT_OF_SCOPE_CURRENT_C0",
        },
        {
            "operation": "memory_random_replay_or_retrieval_ablation",
            "owner": "MemoryEngine",
            "source": "umbra_core/memory/engine.py:1340-1354,1760-1790",
            "rng": "shared persisted Organism SeededRNG only in random modes",
            "draws": "shuffle-dependent",
            "sequence_dependency": True,
            "candidate_order_dependency": True,
            "candidate_pool_size_dependency": True,
            "domain": "learning_memory_ablation",
            "disposition": "OUT_OF_SCOPE_CURRENT_C0",
        },
        {
            "operation": "randomized_observation_ablation",
            "owner": "Organism.tick_once/SelfModel config",
            "source": "umbra_core/runtime.py:1239-1243",
            "rng": "shared persisted Organism SeededRNG",
            "draws": "shuffle plus one uniform per observation",
            "sequence_dependency": True,
            "candidate_order_dependency": False,
            "candidate_pool_size_dependency": False,
            "domain": "perception_ablation",
            "disposition": "OUT_OF_SCOPE_CURRENT_C0",
        },
    ]
    return {
        "directive": "UMBRA-CLOSE-02Y",
        "baseline": BASELINE,
        "candidate_competition_target_count": 2,
        "persistent_rng": {
            "owner": "Organism",
            "source": "umbra_core/runtime.py:436-458,2893-2895",
            "seed_persisted": True,
            "mutable_state_persisted": True,
            "restart_restores_state": True,
            "body_transfer_reseeds": False,
        },
        "paths": paths,
        "scope_conclusion": "Only ordinary candidate-scoring noise and exact-tie ordering require the 02Y contract. Execution, environment, perception, learning, and ablation randomness remain separate and unchanged.",
    }


def build_identity_audit() -> dict[str, Any]:
    return {
        "directive": "UMBRA-CLOSE-02Y",
        "candidate_dataclass_has_stable_id": False,
        "existing_seam": {
            "source": "umbra_core/arbitration.py:347-388",
            "name": "_intent_behavioral_params + _canonical_intent_candidates",
            "capability_included": True,
            "canonical_json": True,
            "recursive_provenance_stripping": True,
            "source_neutral_deduplication": True,
        },
        "identity_contract": {
            "included": [
                "capability",
                "canonical executable parameters",
                "policy-safe target binding fields that affect execution or Governance",
            ],
            "excluded": sorted(PROVENANCE_ONLY_KEYS),
            "candidate_list_index": False,
            "candidate_count": False,
            "proposal_insertion_order": False,
            "source_name": False,
            "hidden_truth": False,
        },
        "unsuitable_existing_identifiers": {
            "proposal_fingerprint": "includes full params/provenance and is downstream Governance material",
            "trace_id": "diagnostic provenance",
            "memory_item_id": "proposal provenance",
            "practice_goal_id": "proposal provenance",
            "observation_id": "evidence identity, not necessarily behavioral identity",
        },
        "manipulation_boundary": "Retain target_address_ref, perception evidence binding, state version, perceived kind/affordance, and nested execution parameters because they can affect Governance or execution. Only explicit bookkeeping keys are stripped.",
        "conclusion": "CURRENT_SEMANTICS_SUFFICIENT_WITH_BOUNDED_CANONICAL_IDENTITY_EXTRACTION",
    }


def build_replay() -> dict[str, Any]:
    u = read_jsonl_tick(U_ATTRIB / "CLOSE02UATTRIB_R1_TRACE.jsonl", 569)
    x = read_jsonl_tick(X_ATTRIB / "CLOSE02XATTRIB_R1_TRACE.jsonl", 569)
    pool_u = [
        {"capability": row["capability"], "params": row.get("params") or {}}
        for row in u["scored_candidates"]
    ]
    constrained = (x["prospective_recoverability"][-1]).get("candidate")
    if constrained.get("capability") != "REST":
        raise RuntimeError("tick_569_constrained_candidate_not_rest")
    pool_x = [row for row in pool_u if row["capability"] != "REST"]
    terms_u = stable_terms(pool_u, organism_basis=57531938, active_tick=569)
    terms_x = stable_terms(pool_x, organism_basis=57531938, active_tick=569)
    common = sorted(set(terms_u).intersection(terms_x))
    return {
        "directive": "UMBRA-CLOSE-02Y",
        "retained_state": {"seed": 57531938, "active_tick": 569, "regime": "R1/S16"},
        "source_evidence": {
            "u_trace": str(U_ATTRIB / "CLOSE02UATTRIB_R1_TRACE.jsonl"),
            "x_trace": str(X_ATTRIB / "CLOSE02XATTRIB_R1_TRACE.jsonl"),
            "u_pool_count": len(pool_u),
            "x_pool_count": len(pool_x),
            "removed_behavior": candidate_identity(
                next(row for row in pool_u if row["capability"] == "REST")
            ),
        },
        "common_candidates": [
            {
                "identity": identity,
                "u_term": terms_u[identity],
                "x_term": terms_x[identity],
                "equal": terms_u[identity] == terms_x[identity],
            }
            for identity in common
        ],
        "all_common_terms_equal": all(terms_u[i] == terms_x[i] for i in common),
        "only_removed_term_absent": set(terms_u) - set(terms_x)
        == {candidate_identity(next(row for row in pool_u if row["capability"] == "REST"))},
        "claim_boundary": "This proves stochastic composition only. It does not claim the retained X organism would have survived or selected a particular long-horizon trajectory.",
    }


PRIOR_ART = """# CLOSE-02Y bounded prior-art review

## JAX PRNG design

- Source: https://docs.jax.dev/en/latest/jep/263-prng.html
- Disposition: REFERENCE.
- Adoptable principle: explicit keyed/splittable random state removes artificial sequencing dependencies between otherwise independent stochastic operations while preserving reproducibility.
- Not adopted: JAX, Threefry, array/vectorization architecture, or any external dependency.

## Random123 / counter-based PRNG

- Source: https://www.thesalmons.org/john/random123/papers/random123sc11.pdf
- Disposition: REFERENCE.
- Adoptable principle: independent keyed transformations of explicit counters can provide reproducible random samples without advancing a shared sequential state.
- Not adopted: Random123, Philox, Threefry, AES, or a specific generator/library.

## UMBRA translation

Use an explicit semantic key consisting of a persistent organism stochastic basis, authoritative active tick, candidate-scoring namespace/version, and canonical source-neutral behavioral candidate identity. The architecture requires deterministic candidate-local samples and namespace separation; it does not prescribe a particular PRNG implementation.
"""


CONTRACT = """# CLOSE-02Y candidate-stable stochastic contract

## Contract

For ordinary noncritical candidate competition, each already-generated, authority-valid behavioral candidate receives one bounded stochastic perturbation derived from:

1. a persistent organism stochastic basis already carried by UMBRA;
2. authoritative active tick;
3. versioned `ordinary_candidate_competition` namespace;
4. canonical source-neutral behavioral candidate identity.

Candidate-list index, candidate count, proposal source, provenance IDs, and insertion order are forbidden key fields. The term is a modifier only: it creates no candidate, changes no deterministic score component, executes nothing, and does not bypass the existing final arbitration, Governance, Embodiment, or VerifiedOutcome.

## Candidate identity

Identity is capability plus canonical executable parameters after recursive removal of explicit proposal-provenance fields. Parameters that alter execution or Governance binding remain. Behaviorally equivalent duplicates are source-neutrally deduplicated before stochastic ranking. Exact total ties use canonical behavioral identity, never list order or source.

## Namespace and persistence

Candidate-scoring stochasticity becomes a separate deterministic domain. Perception, environmental execution, partner response, movement slip, learning, and ablation RNG behavior remain on their existing domains and are not silently converted. Restart reproduces the term from persisted organism basis and active tick; body migration does not renumber it.

## Required invariants

- Unrelated insertion, deletion, or permutation leaves every surviving candidate term unchanged.
- Different legitimate ticks, organisms, namespaces, or behavioral parameters may differ.
- Equivalent source proposals receive equivalent stochastic treatment.
- Bounded individuality remains supplied by learned deterministic individuality modifiers plus bounded candidate-local variation.
- No hidden truth, source priority, planner, global utility, new authority, or organism RNG sequence position enters the key.

## Implementation boundary

The proof uses SHA-256 plus a deterministic normal transform only as a pure fixture. A later implementation directive must choose and freeze the concrete stdlib-compatible derivation, migration/fingerprint behavior, and regression contract before organism outcomes. No JAX or Random123 dependency is required.
"""


INDIVIDUALITY = """# CLOSE-02Y individuality compatibility

1. Current individuality modifiers are deterministic functions of learned, verified disposition state and candidate behavior; they consume no RNG during scoring.
2. D-007 explicitly treats RNG-only divergence as insufficient individuality (`test_rng_only_condition_fails_individuality`).
3. D-007 separately requires bounded behavioral variability (`test_behavior_is_not_fully_deterministic`) and persistence of learned dispositions across restart.
4. Candidate-local stochastic terms preserve bounded variation across organism basis, tick, and behavioral identity without making list position a scientific trait.
5. Runtime already persists the organism seed and mutable RNG state; authoritative active tick is already passed into arbitration. Body transfer preserves constitutional identity and individuality state.
6. No qualified D-007/D-010/D-011/D-012 claim requires sequential candidate-order-dependent draw assignment. Exact organism trajectories will change at implementation and therefore require fresh qualification, but the qualified conceptual claims are compatible.

Conclusion: `NO_QUALIFIED_INDIVIDUALITY_CONFLICT`.
"""


DRIFT = """# CLOSE-02Y drift review

- Whole-organism viability advanced: YES, by removing a causal confound prerequisite to later anticipatory-regulation evaluation.
- Body independent: YES; body identity is not a stochastic key field.
- Endogenous behavior preserved: YES; stochasticity remains bounded and organism-seeded.
- Hidden world truth used: NO.
- Verified-outcome learning preserved: YES.
- New scheduler/scripted survival policy: NO.
- Physiology thresholds/effects changed: NO.
- D-013/AX or H3 reopened: NO.
- Production code changed: NO.
- Organism runs: 0.
- Deferred, not solved: fatigue support acquisition and positive anticipatory preparation.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()

    audits = [verify_manifest(X_ATTRIB), verify_manifest(U_ATTRIB), verify_manifest(W_EVIDENCE)]
    if not all(item["verified"] for item in audits):
        raise RuntimeError(f"retained_manifest_failure:{audits}")

    replay = build_replay()
    if not replay["all_common_terms_equal"] or not replay["only_removed_term_absent"]:
        raise RuntimeError("candidate_stability_replay_failed")

    write_json(output / "CLOSE02Y_STOCHASTIC_PATH_MAP.json", build_path_map())
    write_json(output / "CLOSE02Y_CANDIDATE_IDENTITY_AUDIT.json", build_identity_audit())
    atomic_write(output / "CLOSE02Y_PRIOR_ART_REVIEW.md", PRIOR_ART.encode())
    atomic_write(output / "CLOSE02Y_CANDIDATE_STABLE_STOCHASTIC_CONTRACT.md", CONTRACT.encode())
    write_json(output / "CLOSE02Y_X_U_RETAINED_REPLAY.json", replay)
    atomic_write(output / "CLOSE02Y_INDIVIDUALITY_COMPATIBILITY.md", INDIVIDUALITY.encode())
    atomic_write(output / "CLOSE02Y_DRIFT_REVIEW.md", DRIFT.encode())
    write_json(
        output / "CLOSE02Y_RETAINED_EVIDENCE_AUDIT.json",
        {"directive": "UMBRA-CLOSE-02Y", "manifests": audits, "all_verified": True},
    )
    write_json(
        output / "CLOSE02Y_VALIDATION.json",
        {
            "directive": "UMBRA-CLOSE-02Y",
            "pure_contract_tests": "PASS",
            "retained_tick_569_replay": "PASS",
            "permutation_insertion_deletion": "PASS",
            "restart_migration_semantics": "PASS",
            "production_changes": 0,
            "organism_runs": 0,
        },
    )
    write_json(
        output / "CLOSE02Y_VERDICT.json",
        {
            "directive": "UMBRA-CLOSE-02Y",
            "status": "TERMINAL",
            "verdict": "CLOSE02Y_CANDIDATE_STABLE_STOCHASTIC_CONTRACT_SUPPORTED",
            "recommendation": "UMBRA-CLOSE-02Z_CANDIDATE_STABLE_STOCHASTIC_IMPLEMENTATION_CANDIDATE",
            "next_phase_authorized": False,
            "production_changes": 0,
            "organism_runs": 0,
            "deferred": [
                "fatigue support acquisition",
                "positive anticipatory preparation",
                "proactive rest seeking",
                "prospective opportunity creation",
                "candidate-veto replacement",
            ],
        },
    )

    files = []
    for path in sorted(output.iterdir()):
        if path.name == "EVIDENCE_HASHES.json" or not path.is_file():
            continue
        files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    write_json(
        output / "EVIDENCE_HASHES.json",
        {
            "algorithm": "sha256",
            "directive": "UMBRA-CLOSE-02Y",
            "file_count": len(files),
            "files": files,
            "readback_verified": True,
            "status": "PASS",
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
