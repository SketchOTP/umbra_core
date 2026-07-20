"""Shared helpers for UMBRA core (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import math
import random
import uuid
from typing import Any


SCHEMA_VERSION = "1.0.0"


def new_id() -> str:
    return str(uuid.uuid4())


def canon_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def angle_diff(a: float, b: float) -> float:
    """Smallest signed difference a-b in (-pi, pi]."""
    d = (a - b + math.pi) % (2 * math.pi) - math.pi
    return d


class SeededRNG:
    """Deterministic RNG wrapper — all stochasticity must go through this."""

    def __init__(self, seed: int):
        self.seed = int(seed)
        self._r = random.Random(self.seed)

    def random(self) -> float:
        return self._r.random()

    def uniform(self, a: float, b: float) -> float:
        return self._r.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._r.gauss(mu, sigma)

    def choice(self, seq: list[Any]) -> Any:
        return self._r.choice(seq)

    def shuffle(self, xs: list[Any]) -> None:
        self._r.shuffle(xs)

    def randint(self, a: int, b: int) -> int:
        return self._r.randint(a, b)

    def fork(self, salt: int) -> SeededRNG:
        return SeededRNG(self.seed ^ (salt * 0x9E3779B9) & 0xFFFFFFFF)

    def export_state(self) -> dict[str, Any]:
        version, data, gauss_next = self._r.getstate()
        return {
            "seed": self.seed,
            "version": version,
            "data": list(data),
            "gauss_next": gauss_next,
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self.seed = int(state["seed"])
        data = tuple(state["data"])
        self._r.setstate((int(state["version"]), data, state.get("gauss_next")))
