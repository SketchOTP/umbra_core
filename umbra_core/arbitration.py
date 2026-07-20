"""Action arbitration — vector scoring, hysteresis, anti-thrash. No LLM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umbra_core.embodiment import CAPABILITIES
from umbra_core.physiology import BOUNDS, Physiology
from umbra_core.util import SeededRNG, clamp


@dataclass
class Candidate:
    capability: str
    params: dict[str, Any]
    scores: dict[str, float] = field(default_factory=dict)
    total: float = 0.0


@dataclass
class ArbitrationState:
    last_capability: str | None = None
    last_switch_tick: int = 0
    consecutive_same: int = 0
    retry_counts: dict[str, int] = field(default_factory=dict)
    visited_cells: set[tuple[int, int]] = field(default_factory=set)
    action_counts: dict[str, int] = field(default_factory=dict)
    thrash_events: int = 0
    hysteresis: float = 0.12
    max_retries: int = 4
    search_heading: float = 0.0
    recovery_focus: str | None = None
    # ablation flags
    hide_physiology: bool = False
    mode: str = "full"  # full | random | scripted

    def to_state(self) -> dict[str, Any]:
        return {
            "last_capability": self.last_capability,
            "last_switch_tick": self.last_switch_tick,
            "consecutive_same": self.consecutive_same,
            "retry_counts": dict(self.retry_counts),
            "visited_cells": [list(c) for c in self.visited_cells],
            "action_counts": dict(self.action_counts),
            "thrash_events": self.thrash_events,
            "hysteresis": self.hysteresis,
            "max_retries": self.max_retries,
            "search_heading": self.search_heading,
            "recovery_focus": self.recovery_focus,
            "hide_physiology": self.hide_physiology,
            "mode": self.mode,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> ArbitrationState:
        s = cls(
            last_capability=d.get("last_capability"),
            last_switch_tick=int(d.get("last_switch_tick", 0)),
            consecutive_same=int(d.get("consecutive_same", 0)),
            retry_counts=dict(d.get("retry_counts", {})),
            action_counts=dict(d.get("action_counts", {})),
            thrash_events=int(d.get("thrash_events", 0)),
            hysteresis=float(d.get("hysteresis", 0.12)),
            max_retries=int(d.get("max_retries", 4)),
            search_heading=float(d.get("search_heading", 0.0)),
            recovery_focus=d.get("recovery_focus"),
            hide_physiology=bool(d.get("hide_physiology", False)),
            mode=str(d.get("mode", "full")),
        )
        s.visited_cells = {tuple(c) for c in d.get("visited_cells", [])}
        return s


SCRIPT_CYCLE = ["ORIENT", "MOVE", "MOVE", "INSPECT", "MOVE", "CHARGE", "REST", "IDLE"]


class Arbitrator:
    def __init__(self, state: ArbitrationState | None = None):
        self.state = state or ArbitrationState()

    def generate_candidates(
        self,
        phys: Physiology,
        observations: list[dict[str, Any]],
        tick: int,
    ) -> list[Candidate]:
        obs_by_kind = {o["kind"]: o for o in observations}
        cands: list[Candidate] = [
            Candidate("IDLE", {}),
            Candidate("ORIENT", {"heading": 0.0}),
        ]

        # Orient toward each observed feature
        for kind, o in obs_by_kind.items():
            heading = float(o["relative_direction"])  # relative — body-frame; runtime converts
            cands.append(Candidate("ORIENT", {"heading_delta": heading, "toward": kind}))
            if kind == "resource":
                cands.append(
                    Candidate(
                        "APPROACH",
                        {"heading_delta": heading, "step": 1.0, "toward": "resource"},
                    )
                )
                cands.append(Candidate("CHARGE", {"toward": "resource"}))
            elif kind == "rest":
                cands.append(
                    Candidate(
                        "APPROACH",
                        {"heading_delta": heading, "step": 1.0, "toward": "rest"},
                    )
                )
                cands.append(Candidate("REST", {"toward": "rest"}))
            elif kind == "inspect":
                cands.append(
                    Candidate(
                        "APPROACH",
                        {"heading_delta": heading, "step": 1.0, "toward": "inspect"},
                    )
                )
                cands.append(Candidate("INSPECT", {"toward": "inspect"}))
            elif kind == "hazard":
                cands.append(
                    Candidate(
                        "RETREAT",
                        {"heading_delta": heading, "step": 1.2, "from": "hazard"},
                    )
                )

        cands.append(Candidate("MOVE", {"heading_delta": 0.0, "step": 1.0}))
        cands.append(Candidate("MOVE", {"heading_delta": 0.7, "step": 1.0}))
        cands.append(Candidate("MOVE", {"heading_delta": -0.7, "step": 1.0}))
        return cands

    def score_candidate(
        self,
        cand: Candidate,
        phys: Physiology,
        observations: list[dict[str, Any]],
        tick: int,
    ) -> Candidate:
        obs_by_kind = {o["kind"]: o for o in observations}
        urg = {n: 0.0 for n in BOUNDS} if self.state.hide_physiology else phys.vector_urgency()

        # expected_regulatory_gain
        gain = 0.0
        cap = cand.capability
        toward = cand.params.get("toward") or cand.params.get("from")
        if cap == "CHARGE":
            gain += urg["energy"] * 1.4 - phys.satiation_penalty("energy") * 1.2
        elif cap == "REST":
            gain += urg["fatigue"] * 1.4 - phys.satiation_penalty("fatigue") * 1.2
        elif cap == "INSPECT":
            gain += urg["stimulation"] * 1.2 - phys.satiation_penalty("stimulation") * 0.8
        elif cap == "RETREAT":
            gain += urg["integrity"] * 1.5
        elif cap in ("APPROACH", "MOVE", "ORIENT"):
            if toward == "resource":
                gain += urg["energy"] * 0.7
            elif toward == "rest":
                gain += urg["fatigue"] * 0.7
            elif toward == "inspect":
                gain += urg["stimulation"] * 0.6
            elif toward == "hazard" or cand.params.get("from") == "hazard":
                gain += urg["integrity"] * 0.9
            else:
                # blind exploration scales with unmet needs
                gain += urg["stimulation"] * 0.15
                gain += urg["energy"] * 0.35
                gain += urg["fatigue"] * 0.25
                gain += urg["integrity"] * 0.15

        # option preservation — keep some energy / avoid hazard approaches
        option = 0.2
        if cap in ("MOVE", "APPROACH") and toward == "hazard":
            option -= 0.8
        if phys.energy < 0.25 and cap in ("MOVE", "APPROACH", "INSPECT"):
            option -= 0.3
        if phys.critical_any() and cap not in ("CHARGE", "REST", "RETREAT", "IDLE"):
            option -= 0.5

        # novelty / coverage
        novelty = 0.05
        if cap == "MOVE":
            novelty += 0.15
        if cap == "INSPECT":
            novelty += 0.25

        # uncertainty reduction
        unc_red = 0.0
        for o in observations:
            unc_red += float(o.get("uncertainty", 0)) * 0.05
        if cap == "INSPECT":
            unc_red += 0.2
        if cap == "ORIENT":
            unc_red += 0.05

        # effort / risk
        effort = {
            "IDLE": 0.0,
            "ORIENT": 0.05,
            "MOVE": 0.25,
            "APPROACH": 0.22,
            "RETREAT": 0.25,
            "INSPECT": 0.1,
            "REST": 0.05,
            "CHARGE": 0.08,
        }.get(cap, 0.2)
        risk = 0.0
        if toward == "hazard" and cap != "RETREAT":
            risk += 0.9
        if "hazard" in obs_by_kind and cap == "APPROACH" and toward != "hazard":
            # mild risk if navigating near hazard without retreat
            if float(obs_by_kind["hazard"].get("estimated_distance", 99)) < 3.0:
                risk += 0.25

        # commitment continuity
        continuity = 0.0
        if self.state.last_capability == cap:
            continuity = self.state.hysteresis + 0.05 * min(5, self.state.consecutive_same)
        elif self.state.last_capability is not None:
            # switching cost
            continuity = -0.08
            if tick - self.state.last_switch_tick < 3:
                continuity -= 0.15

        # retry penalty
        retries = self.state.retry_counts.get(cap, 0)
        if retries >= self.state.max_retries:
            gain -= 2.0

        scores = {
            "expected_regulatory_gain": gain,
            "expected_option_preservation": option,
            "novelty": novelty,
            "uncertainty_reduction": unc_red,
            "effort_cost": -effort,
            "risk_cost": -risk,
            "commitment_continuity": continuity,
        }
        cand.scores = scores
        cand.total = sum(scores.values())
        return cand

    def select(
        self,
        phys: Physiology,
        observations: list[dict[str, Any]],
        tick: int,
        rng: SeededRNG,
    ) -> Candidate:
        mode = self.state.mode
        if mode == "random":
            cap = rng.choice(list(CAPABILITIES))
            cand = Candidate(cap, {"step": 1.0, "heading_delta": rng.uniform(-1.0, 1.0)})
            self._commit(cand, tick)
            return cand
        if mode == "scripted":
            cap = SCRIPT_CYCLE[tick % len(SCRIPT_CYCLE)]
            cand = Candidate(cap, {"step": 1.0, "heading_delta": 0.3})
            self._commit(cand, tick)
            return cand

        # recovery reflexes — disabled under physiology-hidden ablation (C3)
        needs = [] if self.state.hide_physiology else phys.needs_recovery()
        if (needs or phys.critical_any()) and not self.state.hide_physiology:
            crit = phys.critical_vars()
            # sticky serialized recovery — finish current focus unless energy critical
            ORDER = ("energy", "fatigue", "integrity", "stimulation")
            pool = set(crit) if crit else set(needs)
            if self.state.recovery_focus and self.state.recovery_focus not in pool:
                self.state.recovery_focus = None
            if (
                self.state.recovery_focus
                and self.state.recovery_focus in pool
                and not (
                    self.state.recovery_focus != "energy"
                    and phys.energy < BOUNDS["energy"].critical_low
                )
            ):
                focus = self.state.recovery_focus
            else:
                focus = next((n for n in ORDER if n in pool), max(pool, key=phys.urgency))
                self.state.recovery_focus = focus
            kinds = {o["kind"] for o in observations}

            def pick_recovery(cands: list[Candidate]) -> Candidate:
                # ignore hysteresis for recovery — break orient thrash
                scored = []
                for c in cands:
                    sc = self.score_candidate(c, phys, observations, tick)
                    sc.total -= sc.scores.get("commitment_continuity", 0.0)
                    if c.capability == "MOVE":
                        sc.total += 0.5
                    if c.capability == "ORIENT":
                        sc.total -= 1.0
                    scored.append(sc)
                scored.sort(key=lambda c: c.total, reverse=True)
                chosen = scored[0]
                self._commit(chosen, tick)
                return chosen

            if focus == "energy":
                if "resource" in kinds:
                    o = next(o for o in observations if o["kind"] == "resource")
                    hd = float(o["relative_direction"])
                    dist = float(o["estimated_distance"])
                    if dist <= 2.2:
                        chosen = Candidate("CHARGE", {"toward": "resource"})
                        self._commit(chosen, tick)
                        return chosen
                    chosen = Candidate(
                        "APPROACH",
                        {"heading_delta": hd, "step": 1.5, "toward": "resource"},
                    )
                    self._commit(chosen, tick)
                    return chosen
                # persistent absolute search heading
                if tick % 9 == 0:
                    self.state.search_heading += 0.9
                chosen = Candidate(
                    "MOVE",
                    {"heading": self.state.search_heading, "step": 1.5},
                )
                self._commit(chosen, tick)
                return chosen
            if focus == "fatigue":
                if "rest" in kinds:
                    o = next(o for o in observations if o["kind"] == "rest")
                    hd = float(o["relative_direction"])
                    dist = float(o["estimated_distance"])
                    if dist <= 2.2:
                        chosen = Candidate("REST", {"toward": "rest"})
                        self._commit(chosen, tick)
                        return chosen
                    chosen = Candidate(
                        "APPROACH",
                        {"heading_delta": hd, "step": 1.4, "toward": "rest"},
                    )
                    self._commit(chosen, tick)
                    return chosen
                if tick % 9 == 0:
                    self.state.search_heading += 0.9
                chosen = Candidate(
                    "MOVE",
                    {"heading": self.state.search_heading, "step": 1.3},
                )
                self._commit(chosen, tick)
                return chosen
            if focus == "integrity":
                # rest repairs integrity; retreat from hazard first
                if "hazard" in kinds:
                    o = next(o for o in observations if o["kind"] == "hazard")
                    if float(o["estimated_distance"]) < 4.0:
                        chosen = Candidate(
                            "RETREAT",
                            {
                                "heading_delta": float(o["relative_direction"]),
                                "step": 1.8,
                                "from": "hazard",
                            },
                        )
                        self._commit(chosen, tick)
                        return chosen
                if "rest" in kinds:
                    o = next(o for o in observations if o["kind"] == "rest")
                    hd = float(o["relative_direction"])
                    if float(o["estimated_distance"]) <= 2.2:
                        chosen = Candidate("REST", {"toward": "rest"})
                        self._commit(chosen, tick)
                        return chosen
                    chosen = Candidate(
                        "APPROACH",
                        {"heading_delta": hd, "step": 1.4, "toward": "rest"},
                    )
                    self._commit(chosen, tick)
                    return chosen
                if tick % 4 == 0:
                    chosen = Candidate("IDLE", {})
                    self._commit(chosen, tick)
                    return chosen
                if tick % 9 == 0:
                    self.state.search_heading += 0.9
                chosen = Candidate(
                    "MOVE",
                    {"heading": self.state.search_heading, "step": 1.4},
                )
                self._commit(chosen, tick)
                return chosen
            if focus == "stimulation":
                # overshoot: calm down via REST/IDLE rather than more inspect/move
                if phys.stimulation > BOUNDS["stimulation"].viable_high:
                    if "rest" in kinds:
                        o = next(o for o in observations if o["kind"] == "rest")
                        if float(o["estimated_distance"]) <= 2.2:
                            chosen = Candidate("REST", {"toward": "rest"})
                            self._commit(chosen, tick)
                            return chosen
                        chosen = Candidate(
                            "APPROACH",
                            {
                                "heading_delta": float(o["relative_direction"]),
                                "step": 1.2,
                                "toward": "rest",
                            },
                        )
                        self._commit(chosen, tick)
                        return chosen
                    chosen = Candidate("IDLE", {})
                    self._commit(chosen, tick)
                    return chosen
                if "inspect" in kinds:
                    o = next(o for o in observations if o["kind"] == "inspect")
                    hd = float(o["relative_direction"])
                    if float(o["estimated_distance"]) <= 2.2:
                        chosen = Candidate("INSPECT", {"toward": "inspect"})
                        self._commit(chosen, tick)
                        return chosen
                    chosen = Candidate(
                        "APPROACH",
                        {"heading_delta": hd, "step": 1.3, "toward": "inspect"},
                    )
                    self._commit(chosen, tick)
                    return chosen
                if tick % 9 == 0:
                    self.state.search_heading += 0.9
                chosen = Candidate(
                    "MOVE",
                    {"heading": self.state.search_heading, "step": 1.3},
                )
                self._commit(chosen, tick)
                return chosen

        cands = self.generate_candidates(phys, observations, tick)
        scored = [self.score_candidate(c, phys, observations, tick) for c in cands]
        # bounded stochasticity: softmax-ish via noisy argmax
        for c in scored:
            c.total += rng.gauss(0.0, 0.08)
        scored.sort(key=lambda c: c.total, reverse=True)
        chosen = scored[0]

        # anti-thrash: if switching every tick among top, stick
        if (
            self.state.last_capability
            and chosen.capability != self.state.last_capability
            and tick - self.state.last_switch_tick <= 1
            and self.state.consecutive_same < 2
        ):
            # prefer continuing previous if within hysteresis band
            prev = next((c for c in scored if c.capability == self.state.last_capability), None)
            if prev and (chosen.total - prev.total) < self.state.hysteresis:
                self.state.thrash_events += 1
                chosen = prev

        self._commit(chosen, tick)
        return chosen

    def _commit(self, cand: Candidate, tick: int) -> None:
        if cand.capability != self.state.last_capability:
            if self.state.last_capability is not None and tick - self.state.last_switch_tick <= 2:
                self.state.thrash_events += 1
            self.state.last_capability = cand.capability
            self.state.last_switch_tick = tick
            self.state.consecutive_same = 1
        else:
            self.state.consecutive_same += 1
        self.state.action_counts[cand.capability] = self.state.action_counts.get(cand.capability, 0) + 1

    def note_outcome(self, capability: str, success: bool) -> None:
        if success:
            self.state.retry_counts[capability] = 0
        else:
            self.state.retry_counts[capability] = self.state.retry_counts.get(capability, 0) + 1
