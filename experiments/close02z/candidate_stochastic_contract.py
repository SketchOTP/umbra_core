"""Pure CLOSE-02Z candidate-stable stochastic contract proof.

This module is not imported by organism production execution.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable, Mapping


CONTRACT_SCHEMA = "CANDIDATE_STABLE_STOCHASTIC_TERM_V1"
COMPETITION_NAMESPACE = "ordinary_candidate_competition:v1"
NOISE_SIGMA = 0.08
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


def behavioral_identity(candidate: Mapping[str, Any]) -> str:
    payload = {
        "capability": str(candidate["capability"]),
        "params": _normalize(candidate.get("params") or {}),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _uniform_pair(payload: bytes) -> tuple[float, float]:
    digest = hashlib.sha256(payload).digest()
    scale = float(1 << 64)
    return (
        (int.from_bytes(digest[:8], "big") + 0.5) / scale,
        (int.from_bytes(digest[8:16], "big") + 0.5) / scale,
    )


def candidate_stochastic_term(
    candidate: Mapping[str, Any],
    *,
    organism_basis: int | str,
    active_tick: int,
    namespace: str = COMPETITION_NAMESPACE,
    sigma: float = NOISE_SIGMA,
) -> float:
    key = {
        "schema": CONTRACT_SCHEMA,
        "namespace": str(namespace),
        "organism_basis": str(organism_basis),
        "active_tick": int(active_tick),
        "candidate_identity": behavioral_identity(candidate),
    }
    encoded = json.dumps(key, sort_keys=True, separators=(",", ":")).encode()
    u1, u2 = _uniform_pair(encoded)
    standard_normal = math.sqrt(-2.0 * math.log(u1)) * math.cos(
        2.0 * math.pi * u2
    )
    return float(sigma) * standard_normal


def candidate_terms(
    candidates: Iterable[Mapping[str, Any]],
    *,
    organism_basis: int | str,
    active_tick: int,
    namespace: str = COMPETITION_NAMESPACE,
) -> dict[str, float]:
    return {
        behavioral_identity(candidate): candidate_stochastic_term(
            candidate,
            organism_basis=organism_basis,
            active_tick=active_tick,
            namespace=namespace,
        )
        for candidate in candidates
    }
