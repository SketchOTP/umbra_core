"""Durable evidence writer for UMBRA-AS-003N.

This helper deliberately imports no UMBRA modules.  It atomically writes the
JSON records that describe the governed substrate implementation; it cannot
construct an organism or invoke live runtime behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003n-hypothetical-transition-substrate-r1"
)
BASELINE = "d310c21168bf7be918014328257261db4c805a13"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def write_json(name: str, payload: object) -> str:
    if Path(name).name != name or not name.endswith(".json"):
        raise ValueError("evidence artifact name must be a local .json filename")
    ROOT.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(payload)
    fd, temp_name = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, ROOT / name)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    written = (ROOT / name).read_bytes()
    if written != data:
        raise RuntimeError("readback mismatch")
    return hashlib.sha256(written).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?")
    parser.add_argument("payload", nargs="?")
    parser.add_argument("--write-locks", action="store_true")
    args = parser.parse_args()
    if args.write_locks:
        contract = {
            "schema": "AS003N_SUBSTRATE_CONTRACT_LOCK_V1",
            "baseline": BASELINE,
            "state_schema": {
                "immutable_fields": ["root_tick", "elapsed_time", "physiology_branches", "body_schema", "opportunities", "routes", "pending_commitment", "provenance", "dependencies", "fingerprint", "depth"],
                "forbidden_live_references": ["Physiology", "SelfModel", "WorldModel", "Runtime", "Persistence", "Governance", "Embodiment"],
            },
            "evidence_schema": {"semantics": ["HARD_CONTRACT", "VERIFIED_OBSERVED_SUPPORT", "PROBABILISTIC_SUPPORT", "UNKNOWN", "NOT_APPLICABLE"], "finite_interval_or_unknown": True, "provenance_bound": 16, "canonical_ordering": "lexicographic canonical JSON"},
            "transition_result_schema": {"status": ["SUPPORTED", "UNSUPPORTED", "UNKNOWN"], "successors": "immutable bounded tuple", "reasons": "bounded enum", "no_rng": True, "referentially_transparent": True},
            "semantic_strength_order": ["HARD_CONTRACT", "VERIFIED_OBSERVED_SUPPORT", "PROBABILISTIC_SUPPORT", "UNKNOWN"],
            "composition": {"never_strengthens_evidence": True, "probabilistic_required_for_feasibility": "UNKNOWN", "unknown_required": "UNKNOWN", "not_applicable": "excluded_only_when_semantically_irrelevant", "outward_numeric_enclosure": True},
            "branch_representation": {"correlated_effects": "one immutable full-state branch", "no_independent_field_extrema_merge": True, "overflow": "UNKNOWN:BRANCH_CEILING_EXCEEDED", "no_pruning_sampling_or_likely_branch": True},
            "invalidation_dependencies": ["organism_tick", "physiology_root", "body_schema", "self_model", "world_model", "habitat", "opportunity", "pending_commitment", "capability_support"],
            "service_validation": {"non_executable": True, "non_authoritative": True, "requires_supported_preconditions_route_timing_effects": True, "insufficient": "UNKNOWN", "known_invalid": "UNSUPPORTED", "no_best_service_selection": True},
            "canonical_identity": "sha256(canon_json(sorted dependency/value representation))",
            "prohibited": ["planner", "search", "runtime import", "arbitration integration", "live owner mutation", "learning", "persistence", "Governance execution", "Embodiment execution", "organism RNG", "weights", "utility", "source priority"],
        }
        branch_bound = {
            "schema": "AS003N_BRANCH_BOUND_DERIVATION_V1",
            "baseline": BASELINE,
            "source_basis": {"function": "umbra_core.physiology.verified_outcome_effect_branches", "max_current_effect_branch_count": 2, "deterministic_capabilities": ["IDLE", "SIGNAL_PLAY", "SIGNAL_ASSISTANCE"], "delayed_orient_branches": 2},
            "constitutional_bound": {"current_action_steps": 1, "validated_corrective_service_witnesses": 4, "max_composed_steps": 5, "max_exact_correlated_paths": 32, "derivation": "2^5; one current action plus at most one service witness for each of the four protected drives"},
            "correlation_rule": "each path retains the complete coupled effect vector for every step", "overflow_behavior": "UNKNOWN:BRANCH_CEILING_EXCEEDED", "forbidden": ["scalar pruning", "sampling", "likely-branch choice", "independent per-field extrema merge"],
        }
        composition = {
            "schema": "AS003N_EVIDENCE_COMPOSITION_CONTRACT_V1",
            "baseline": BASELINE,
            "reuse": "umbra_core.self_model.engine.SupportSemantics",
            "rules": {"HARD_CONTRACT": "may support an applicable fact", "VERIFIED_OBSERVED_SUPPORT": "only within its observed envelope", "PROBABILISTIC_SUPPORT": "UNKNOWN for categorical existential feasibility", "UNKNOWN": "UNKNOWN", "NOT_APPLICABLE": "excluded only when semantically irrelevant"},
            "monotonicity": "composition preserves or weakens support quality; it never improves it", "no_imagined_upgrade": ["UNKNOWN->SUPPORTED", "PROBABILISTIC_SUPPORT->VERIFIED_OBSERVED_SUPPORT"],
        }
        outputs = {name: write_json(name, payload) for name, payload in (("AS003N_SUBSTRATE_CONTRACT_LOCK.json", contract), ("AS003N_BRANCH_BOUND_DERIVATION.json", branch_bound), ("AS003N_EVIDENCE_COMPOSITION_CONTRACT.json", composition))}
        print(json.dumps(outputs, sort_keys=True))
        return
    if args.name is None or args.payload is None:
        parser.error("name and payload are required unless --write-locks is used")
    print(write_json(args.name, json.loads(args.payload)))


if __name__ == "__main__":
    main()
