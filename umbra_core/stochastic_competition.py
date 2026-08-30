"""Versioned candidate-local stochasticity for ordinary action competition."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


CONTRACT_SCHEMA = "CANDIDATE_STABLE_STOCHASTIC_TERM_V1"
CANDIDATE_COMPETITION_NAMESPACE = "ordinary_candidate_competition:v1"
CANDIDATE_NOISE_SIGMA = 0.08

# Proposal bookkeeping does not define executable behavioral identity.  Fields
# that bind Governance or execution (target refs, perception state, affordance,
# executable parameters) deliberately remain.
PROVENANCE_ONLY_KEYS = frozenset(
    {
        "source",
        "memory_item_id",
        "practice_goal_id",
        "routine_skill_id",
        "goal_id",
        "trace_id",
        "provenance",
        "proposal_id",
        "supporting_evidence_refs",
    }
)


def _normalize_behavioral_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_behavioral_value(item)
            for key, item in value.items()
            if str(key) not in PROVENANCE_ONLY_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_behavioral_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non_finite_behavioral_parameter")
        return 0.0 if value == 0.0 else value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported_behavioral_parameter:{type(value).__name__}")


def candidate_behavioral_identity(capability: str, params: Mapping[str, Any]) -> str:
    """Return canonical source-neutral executable identity."""
    payload = {
        "capability": str(capability),
        "params": _normalize_behavioral_value(params),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def candidate_stochastic_term(
    *,
    organism_basis: int | str,
    active_tick: int,
    capability: str,
    params: Mapping[str, Any],
    namespace: str = CANDIDATE_COMPETITION_NAMESPACE,
    sigma: float = CANDIDATE_NOISE_SIGMA,
) -> float:
    """Derive one zero-centered candidate-local Gaussian perturbation.

    The explicit semantic key removes candidate-list sequencing dependency.
    SHA-256 supplies deterministic bounded key separation; Box-Muller retains
    the existing normal-distribution and scale semantics.
    """
    key = {
        "schema": CONTRACT_SCHEMA,
        "namespace": str(namespace),
        "organism_basis": str(organism_basis),
        "active_tick": int(active_tick),
        "candidate_identity": candidate_behavioral_identity(capability, params),
    }
    encoded = json.dumps(key, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).digest()
    scale = float(1 << 64)
    u1 = (int.from_bytes(digest[:8], "big") + 0.5) / scale
    u2 = (int.from_bytes(digest[8:16], "big") + 0.5) / scale
    standard_normal = math.sqrt(-2.0 * math.log(u1)) * math.cos(
        2.0 * math.pi * u2
    )
    return float(sigma) * standard_normal
