"""Pure evaluator for the CLOSE-02Y candidate-stable stochastic contract.

This module is research-only.  It does not participate in organism execution.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable, Mapping


CONTRACT_SCHEMA = "CANDIDATE_STABLE_STOCHASTIC_TERM_V1"
DEFAULT_NAMESPACE = "ordinary_candidate_competition:v1"

# These fields establish proposal provenance, not executable behavior.  The
# exact list extends Arbitrator._intent_behavioral_params only where current
# source inspection proves the value is bookkeeping rather than an execution
# or Governance binding.
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


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in value.items()
            if str(key) not in PROVENANCE_ONLY_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non_finite_behavioral_parameter")
        return 0.0 if value == 0.0 else value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported_behavioral_parameter:{type(value).__name__}")


def candidate_identity(candidate: Mapping[str, Any]) -> str:
    """Canonical source-neutral identity of an executable behavior request."""
    capability = str(candidate["capability"])
    params = _normalize(candidate.get("params") or {})
    payload = {"capability": capability, "params": params}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _uniform_pair(payload: bytes) -> tuple[float, float]:
    digest = hashlib.sha256(payload).digest()
    # Open interval values from two independent 64-bit digest lanes.
    scale = float(1 << 64)
    u1 = (int.from_bytes(digest[:8], "big") + 0.5) / scale
    u2 = (int.from_bytes(digest[8:16], "big") + 0.5) / scale
    return u1, u2


def stochastic_term(
    candidate: Mapping[str, Any],
    *,
    organism_basis: int | str,
    active_tick: int,
    namespace: str = DEFAULT_NAMESPACE,
    sigma: float = 0.08,
) -> float:
    """Return a deterministic candidate-local normal perturbation.

    SHA-256 and Box-Muller are a bounded proof vehicle, not a prescribed
    production PRNG implementation.
    """
    key = {
        "schema": CONTRACT_SCHEMA,
        "namespace": str(namespace),
        "organism_basis": str(organism_basis),
        "active_tick": int(active_tick),
        "candidate_identity": candidate_identity(candidate),
    }
    encoded = json.dumps(key, sort_keys=True, separators=(",", ":")).encode("utf-8")
    u1, u2 = _uniform_pair(encoded)
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return float(sigma) * z


def stable_terms(
    candidates: Iterable[Mapping[str, Any]],
    *,
    organism_basis: int | str,
    active_tick: int,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, float]:
    """Return one term per canonical behavior, independent of list order."""
    result: dict[str, float] = {}
    for candidate in candidates:
        identity = candidate_identity(candidate)
        result[identity] = stochastic_term(
            candidate,
            organism_basis=organism_basis,
            active_tick=active_tick,
            namespace=namespace,
        )
    return result


def canonical_deduplicate(
    candidates: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate source-equivalent behaviors with deterministic ordering."""
    by_identity: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        identity = candidate_identity(candidate)
        encoded = json.dumps(candidate, sort_keys=True, separators=(",", ":"))
        current = by_identity.get(identity)
        if current is None or encoded < json.dumps(
            current, sort_keys=True, separators=(",", ":")
        ):
            by_identity[identity] = dict(candidate)
    return [by_identity[key] for key in sorted(by_identity)]


def stable_rank(
    candidates: Iterable[Mapping[str, Any]],
    deterministic_totals: Mapping[str, float],
    *,
    organism_basis: int | str,
    active_tick: int,
) -> list[str]:
    """Rank without list-order tie semantics; returns canonical identities."""
    identities = {
        candidate_identity(candidate): candidate
        for candidate in canonical_deduplicate(candidates)
    }
    return sorted(
        identities,
        key=lambda identity: (
            -(
                float(deterministic_totals[identity])
                + stochastic_term(
                    identities[identity],
                    organism_basis=organism_basis,
                    active_tick=active_tick,
                )
            ),
            identity,
        ),
    )
