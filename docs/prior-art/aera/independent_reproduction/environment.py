"""Deterministic embodied micro-world for Track 5 causal experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ACTIONS = (
    "approach_sphere",
    "approach_cube",
    "approach_distractor",
    "grab",
    "release",
    "wait",
)


@dataclass
class EnvConfig:
    delay: int = 1
    action_cost: float = 1.0
    rule_change_at: int | None = None


@dataclass
class World:
    cfg: EnvConfig = field(default_factory=EnvConfig)
    agent_near: str | None = None
    holding: str | None = None
    sphere_held: bool = False
    cube_held: bool = False
    distractor_lit: bool = False
    pending: tuple[str, int] | None = None  # (outcome, ticks_left)
    pending_hold: str | None = None
    t: int = 0
    sphere_grabbable: bool = True  # hidden rule; flips on change
    rule_version: int = 0
    total_cost: float = 0.0
    log: list[dict] = field(default_factory=list)

    def reset(self, seed: int = 0) -> dict:
        _ = seed
        self.agent_near = None
        self.holding = None
        self.sphere_held = False
        self.cube_held = False
        self.distractor_lit = False
        self.pending = None
        self.pending_hold = None
        self.t = 0
        self.sphere_grabbable = True
        self.rule_version = 0
        self.total_cost = 0.0
        self.log.clear()
        return self.observe()

    def features(self) -> tuple[str, ...]:
        f: list[str] = []
        if self.agent_near:
            f.append(f"near:{self.agent_near}")
        if self.holding:
            f.append(f"holding:{self.holding}")
        if self.distractor_lit:
            f.append("cue:distractor_lit")
        f.append(f"rule_v:{self.rule_version}")
        return tuple(sorted(f))

    def observe(self) -> dict:
        return {
            "t": self.t,
            "agent_near": self.agent_near,
            "holding": self.holding,
            "sphere_held": self.sphere_held,
            "cube_held": self.cube_held,
            "distractor_lit": self.distractor_lit,
            "features": self.features(),
            "rule_version": self.rule_version,
        }

    def _resolve_pending(self) -> str | None:
        if not self.pending:
            return None
        outcome, left = self.pending
        # delay=1 → resolve on the next step
        if left > 1:
            self.pending = (outcome, left - 1)
            return None
        self.pending = None
        if outcome.startswith("grab_ok_") and self.pending_hold:
            obj = self.pending_hold
            self.holding = obj
            if obj == "sphere":
                self.sphere_held = True
            if obj == "cube":
                self.cube_held = True
            self.pending_hold = None
        return outcome

    def step(self, action: str) -> tuple[dict, str, dict]:
        if action not in ACTIONS:
            raise ValueError(action)
        info: dict[str, Any] = {}
        self.total_cost += self.cfg.action_cost

        if self.cfg.rule_change_at is not None and self.t == self.cfg.rule_change_at:
            self.sphere_grabbable = False
            self.rule_version += 1
            info["rule_changed"] = True

        realized = self._resolve_pending()
        outcome = realized or "noop"

        # Misleading correlation cue (not causal for grab success)
        self.distractor_lit = self.agent_near == "sphere"

        if action.startswith("approach_"):
            target = action.split("_", 1)[1]
            self.agent_near = target
            self.distractor_lit = target == "sphere"
            outcome = f"near_{target}"
        elif action == "release":
            if self.holding:
                held = self.holding
                self.holding = None
                if held == "sphere":
                    self.sphere_held = False
                if held == "cube":
                    self.cube_held = False
                outcome = f"released_{held}"
            else:
                outcome = "release_fail"
        elif action == "wait":
            outcome = realized or "waited"
        elif action == "grab":
            obj = self.agent_near
            ok = False
            if obj in ("sphere", "cube") and self.holding is None:
                if obj == "sphere":
                    ok = self.sphere_grabbable
                else:
                    ok = True
            result = f"grab_ok_{obj}" if ok and obj else "grab_fail"
            if self.cfg.delay > 0:
                self.pending = (result, self.cfg.delay)
                self.pending_hold = obj if ok else None
                outcome = "grab_pending"
            else:
                if ok and obj:
                    self.holding = obj
                    if obj == "sphere":
                        self.sphere_held = True
                    if obj == "cube":
                        self.cube_held = True
                outcome = result

        self.t += 1
        obs = self.observe()
        self.log.append({"t": self.t, "action": action, "outcome": outcome, "obs": obs})
        return obs, outcome, info
