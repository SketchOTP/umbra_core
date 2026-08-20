"""Frozen AX protocol description and deterministic identity primitives.

This module is metadata-only. It contains no UMBRA organism imports and cannot
launch a scientific AX branch.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


AX_PROTOCOL: dict[str, Any] = {
    "directive": "UMBRA-D-013AX",
    "scientific_baseline": "706f64fbd28686d27a727f6ddcd0345774282530",
    "targets": [
        {"scenario": "default-13035", "seed": 13035, "condition": "C0", "intervention": "I0", "boundary": 254, "failure": 271},
        {"scenario": "heldout-default-13103", "seed": 13103, "condition": "C0", "intervention": "I0", "boundary": 259, "failure": 264},
        {"scenario": "heldout-body-I1-13109", "seed": 13109, "condition": "C0", "intervention": "I1", "boundary": 221, "failure": 261},
    ],
    "start_window": {"from": "accepted recoverability boundary", "through": "baseline failure inclusive", "maximum_decisions": 109},
    "prefix_depths": [2, 3, 4],
    "candidate_sources": "existing policy-visible authority-valid source candidates only",
    "candidate_eligibility": ["source_existing", "policy_visible", "authority_valid"],
    "counterfactual_evolution": "normal governance, final authority, verified outcome, then production-native continuation",
    "authority_path": "existing final authority and verified outcome semantics",
    "drift_effect_semantics": "unchanged production semantics",
    "rng_semantics": "restore exact decision RNG/reference state; no reseeding",
    "dedup_state": ["authoritative organism state", "habitat state", "recovery focus", "pending commitment", "body schema/generation", "policy-visible observations", "RNG state", "remaining forced depth"],
    "release_behavior": "after forced prefix, release to unmodified production",
    "baseline_failure_screen": "viability and no_safe_action at corresponding baseline failure tick",
    "long_run_horizon": 7200,
    "classification_rules": ["EARLIER_FAILURE", "NO_EFFECT", "DELAY_ONLY", "PRELIMINARY_RESCUE", "DIFFERENT_FAILURE_FAMILY", "UNRESOLVED"],
    "generality_gate": {"minimum_independent_targets": 2, "same_source_mechanism": True, "substantive_long_run_rescue": True},
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def protocol_fingerprint(protocol: dict[str, Any] | None = None) -> str:
    return sha256(protocol or AX_PROTOCOL)


def state_fingerprint(state: dict[str, Any]) -> str:
    return sha256(state)


def action_fingerprint(action: dict[str, Any]) -> str:
    return sha256(action)


def branch_id(
    *,
    protocol_fp: str,
    target: str,
    start_tick: int,
    prefix_depth: int,
    parent_branch_id: str | None,
    action: dict[str, Any],
    input_state_hash: str,
    rng_state_hash: str,
    remaining_forced_depth: int,
) -> str:
    payload = {
        "protocol_fingerprint": protocol_fp,
        "target": target,
        "start_tick": int(start_tick),
        "prefix_depth": int(prefix_depth),
        "parent_logical_branch_id": parent_branch_id,
        "candidate_action": action,
        "counterfactual_input_state_hash": input_state_hash,
        "rng_state_reference_hash": rng_state_hash,
        "remaining_forced_depth": int(remaining_forced_depth),
    }
    return "branch:" + sha256(payload)


def synthetic_branch_spec(parent_id: str | None, ordinal: int, depth: int = 0) -> dict[str, Any]:
    """Deterministic non-scientific graph used only for AXH qualification."""
    return {
        "target": "synthetic-target",
        "start_tick": 10,
        "prefix_depth": depth,
        "parent_branch_id": parent_id,
        "action": {"capability": "SYNTHETIC_ACTION", "ordinal": int(ordinal)},
        "input_state_hash": sha256({"parent": parent_id, "ordinal": int(ordinal), "depth": depth}),
        "rng_state_hash": sha256({"rng": "synthetic", "parent": parent_id, "ordinal": int(ordinal)}),
        "remaining_forced_depth": max(0, 4 - depth),
    }
