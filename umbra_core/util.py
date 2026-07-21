"""Shared helpers for UMBRA core (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import resource
import uuid
from typing import Any, Generic, Iterable, Iterator, Sequence, TypeVar


SCHEMA_VERSION = "1.0.0"

T = TypeVar("T")


class BoundedRing(Generic[T]):
    """Fixed-capacity ring buffer — slots allocated at construction (steady RSS)."""

    __slots__ = ("_buf", "_maxlen", "_start", "_len")

    def __init__(self, maxlen: int, initial: Iterable[T] | None = None):
        if maxlen < 1:
            raise ValueError("maxlen_must_be_positive")
        self._maxlen = int(maxlen)
        self._buf: list[T | None] = [None] * self._maxlen
        self._start = 0
        self._len = 0
        if initial is not None:
            for item in initial:
                self.append(item)

    @property
    def maxlen(self) -> int:
        return self._maxlen

    def __len__(self) -> int:
        return self._len

    def __iter__(self) -> Iterator[T]:
        for i in range(self._len):
            yield self._buf[(self._start + i) % self._maxlen]  # type: ignore[misc]

    def __getitem__(self, index: int | slice) -> T | list[T]:
        if isinstance(index, slice):
            return list(self)[index]
        n = self._len
        if index < 0:
            index += n
        if index < 0 or index >= n:
            raise IndexError("ring_index")
        return self._buf[(self._start + index) % self._maxlen]  # type: ignore[return-value]

    def append(self, item: T) -> None:
        if self._len < self._maxlen:
            self._buf[(self._start + self._len) % self._maxlen] = item
            self._len += 1
            return
        self._buf[self._start] = item
        self._start = (self._start + 1) % self._maxlen

    def reclaim_oldest(self) -> T | None:
        """When full, return oldest object for in-place rewrite (no new alloc)."""
        if self._len < self._maxlen:
            return None
        return self._buf[self._start]  # type: ignore[return-value]

    def advance_after_reclaim(self) -> None:
        """Rotate start after reclaim_oldest + in-place rewrite."""
        if self._len < self._maxlen:
            raise RuntimeError("reclaim_advance_on_partial_ring")
        self._start = (self._start + 1) % self._maxlen

    def clear(self) -> None:
        """Drop logical entries; keep preallocated slot array."""
        for i in range(self._maxlen):
            self._buf[i] = None
        self._start = 0
        self._len = 0

    def reset_from(self, items: Sequence[T]) -> None:
        self.clear()
        for item in items[-self._maxlen :]:
            self.append(item)

    def as_list(self) -> list[T]:
        return list(self)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BoundedRing):
            return list(self) == list(other)
        if isinstance(other, list):
            return list(self) == other
        return NotImplemented

    def __repr__(self) -> str:
        return f"BoundedRing(maxlen={self._maxlen}, data={list(self)!r})"


def current_rss_mib(pid: int | None = None) -> float:
    """Current resident set size from /proc VmRSS (not peak ru_maxrss/VmHWM)."""
    pid = os.getpid() if pid is None else int(pid)
    with open(f"/proc/{pid}/status", encoding="utf-8") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    raise RuntimeError("VmRSS_missing")


def peak_rss_mib() -> float:
    """Linux peak RSS high-water (ru_maxrss, KiB). Not a leak-slope signal."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def ols_slope(xs: list[float], ys: list[float]) -> float:
    """Ordinary least-squares slope of y vs x. Returns 0.0 if undefined."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0.0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den



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
