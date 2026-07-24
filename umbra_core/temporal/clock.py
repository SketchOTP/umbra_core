"""TrustedSample and trusted clock helpers (pure)."""

from __future__ import annotations

from dataclasses import dataclass

from umbra_core.temporal.state import canonical_serialize
from umbra_core.util import canon_json, sha256_hex


@dataclass(frozen=True)
class TrustedSample:
    session_id: str
    monotonic_ns: int
    optional_wall_time: float | None
    wall_time_source: str | None
    wall_time_uncertainty: float
    sample_sequence: int


def compute_sample_hash(sample: TrustedSample) -> str:
    return sha256_hex(canon_json(canonical_serialize(sample)))
