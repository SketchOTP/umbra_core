"""External active-runtime accounting; no organism temporal writes."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass
class ActiveRuntime:
    committed_seconds: float = 0.0
    interval_started: float | None = None
    def start(self, now: float) -> None:
        if self.interval_started is not None: raise ValueError("duplicate_interval")
        self.interval_started = now
    def stop(self, now: float) -> float:
        if self.interval_started is None or now < self.interval_started: raise ValueError("invalid_interval")
        self.committed_seconds += now - self.interval_started
        self.interval_started = None
        return self.committed_seconds
    def to_dict(self) -> dict[str, float | None]:
        return {"committed_seconds": self.committed_seconds, "interval_started": self.interval_started}
    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ActiveRuntime":
        return cls(float(data["committed_seconds"]), None if data.get("interval_started") is None else float(data["interval_started"]))
