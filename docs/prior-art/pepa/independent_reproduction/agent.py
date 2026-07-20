"""Layered autonomy agent: Sys1 skills / Sys2 planning / Sys3 goals.

No LLM. Personality bias (C2/C3) is an authored negative control only.
UMBRA individuality under test arises from homeostasis, memory, causal
learning, embodiment, and lived history — not Big Five prompts.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

from world import SKILLS, UNSAFE_WHEN_CRITICAL, Body, Physiology, World

MAX_MEMORY = 256
MAX_GOALS = 6
MAX_RETRIES = 4
REFLECT_EVERY = 400
MAX_GOAL_GEN_PER_REFLECT = 2


@dataclass
class Goal:
    name: str
    drive: str
    priority: float
    source: str
    retries: int = 0
    active: bool = True


@dataclass
class MemoryStore:
    events: deque = field(default_factory=lambda: deque(maxlen=MAX_MEMORY))
    action_success: Counter = field(default_factory=Counter)
    action_fail: Counter = field(default_factory=Counter)
    # preference scores shaped by history (can go negative)
    preference: dict[str, float] = field(
        default_factory=lambda: {a: 0.0 for a in SKILLS}
    )
    randomized: bool = False
    rng: random.Random = field(default_factory=random.Random)

    def record(self, action: str, ok: bool, outcome: dict[str, Any]) -> None:
        if self.randomized:
            action = self.rng.choice(list(SKILLS))
            ok = self.rng.random() < 0.5
        self.events.append((action, ok, outcome.get("reason")))
        if ok:
            self.action_success[action] += 1
            self.preference[action] = min(2.0, self.preference.get(action, 0.0) + 0.08)
        else:
            self.action_fail[action] += 1
            self.preference[action] = max(-2.0, self.preference.get(action, 0.0) - 0.12)

    def success_rate(self, action: str) -> float:
        s = self.action_success[action]
        f = self.action_fail[action]
        n = s + f
        if n == 0:
            return 0.5
        return s / n

    def pref(self, action: str) -> float:
        return self.preference.get(action, 0.0)


@dataclass
class CausalModels:
    support: Counter = field(default_factory=Counter)

    def observe(self, action: str, ok: bool) -> None:
        if ok:
            self.support[action] += 1

    def score(self, action: str) -> float:
        return float(self.support.get(action, 0)) * 0.02


PERSONALITY_BIAS = {
    "lazy": {"idle": 0.35, "rest": 0.3, "social": 0.2, "explore": 0.05, "play": 0.05, "move": 0.05},
    "playful": {"play": 0.35, "explore": 0.2, "social": 0.15, "move": 0.15, "rest": 0.1, "idle": 0.05},
    "curious": {"explore": 0.4, "move": 0.2, "play": 0.15, "social": 0.1, "idle": 0.1, "rest": 0.05},
}

DRIVE_TO_SKILL = {
    "energy": "eat",
    "play": "play",
    "social": "social",
    "curiosity": "explore",
}


class Agent:
    def __init__(
        self,
        condition: str,
        seed: int,
        *,
        personality: str | None = None,
        use_reflection: bool = True,
        embodiment_costs: bool = True,
        randomize_memory: bool = False,
    ):
        self.condition = condition
        self.rng = random.Random(seed)
        self.personality = personality or "playful"
        self.use_reflection = bool(use_reflection) and condition in ("C6", "C8", "C9")
        self.body = Body(cost_scale=0.0 if (not embodiment_costs or condition == "C8") else 1.0)
        self.phys = Physiology()
        self.memory = MemoryStore(
            randomized=randomize_memory or condition == "C9",
            rng=random.Random(seed + 17),
        )
        self.models = CausalModels()
        self.goals: list[Goal] = []
        self.tick = 0
        self.actions_taken: list[str] = []
        self.goal_switches = 0
        self._last_goal: str | None = None
        self.external_blocked = 0
        self.external_accepted = 0
        self.reflections = 0
        self.goals_generated = 0
        self.idle_ticks = 0
        self.meaningful_ticks = 0
        self.goal_completions = 0
        self.script_phase = 0
        self.llm_style_budget = 0
        self.reflect_bonus: dict[str, float] = {a: 0.0 for a in SKILLS}
        # Sys3-style intrinsic weights — only updated by reflection (C7 stays flat).
        self.goal_weights: dict[str, float] = {a: 1.0 for a in SKILLS}
        self._cfg_flags(condition)

    def _cfg_flags(self, c: str) -> None:
        self.use_homeostasis = c in ("C4", "C5", "C6", "C7", "C8", "C9")
        self.use_memory = c in ("C5", "C6", "C7", "C8", "C9")
        self.use_causal = c in ("C5", "C6", "C7", "C8", "C9")
        self.use_personality = c in ("C2", "C3")
        self.use_llm_goals = c == "C3"
        self.use_arbitration = c in ("C6", "C7", "C8", "C9")
        self.use_governance = c in ("C6", "C7", "C8", "C9")
        self.use_layered_goals = c in ("C6", "C7", "C8", "C9")

    def snapshot(self) -> dict[str, Any]:
        return {
            "energy": self.phys.energy,
            "play": self.phys.play,
            "social": self.phys.social,
            "curiosity": self.phys.curiosity,
            "battery": self.body.battery,
            "pos": self.body.position,
            "mem_len": len(self.memory.events),
            "pref": dict(self.memory.preference),
        }

    def restore_continuity(self, snap: dict[str, Any]) -> None:
        self.phys.energy = snap["energy"]
        self.phys.play = snap["play"]
        self.phys.social = snap["social"]
        self.phys.curiosity = snap["curiosity"]
        self.body.battery = snap["battery"]
        self.body.position = snap["pos"]
        if "pref" in snap:
            self.memory.preference.update(snap["pref"])

    def enqueue_external(self, name: str, priority: float = 0.9) -> bool:
        if self.use_governance and self.phys.critical_energy():
            if name in UNSAFE_WHEN_CRITICAL or name in {"explore", "play"}:
                self.external_blocked += 1
                return False
        active_n = sum(1 for g in self.goals if g.active)
        if active_n >= MAX_GOALS:
            self.external_blocked += 1
            return False
        self.goals.append(
            Goal(name=name, drive="external", priority=priority, source="external")
        )
        self.external_accepted += 1
        return True

    def _drive_scores(self) -> dict[str, float]:
        d = self.phys.drives()
        scores = {
            "eat": d["energy"] * 1.4,
            "charge": (d["energy"] * 1.2) + (0.5 if self.body.battery < 0.35 else 0.0),
            "play": d["play"],
            "social": d["social"],
            "explore": d["curiosity"],
            "move": 0.15,
            "rest": 0.1 + self.body.fatigue,
            "idle": 0.05,
        }
        # satiation: when drive low, suppress corresponding action hard
        if self.phys.play < 0.25:
            scores["play"] *= 0.15
        if self.phys.social < 0.25:
            scores["social"] *= 0.15
        if self.phys.curiosity < 0.25:
            scores["explore"] *= 0.15
        if self.phys.energy > 0.7:
            scores["eat"] *= 0.2
            scores["charge"] *= 0.3

        if self.use_memory:
            for a in SKILLS:
                scores[a] = scores.get(a, 0.0) + 0.35 * self.memory.pref(a)
        if self.use_causal:
            for a in SKILLS:
                scores[a] = scores.get(a, 0.0) + self.models.score(a)
        if self.use_reflection:
            for a in SKILLS:
                scores[a] = scores.get(a, 0.0) + self.reflect_bonus.get(a, 0.0)
        # goal_weights always applied; only reflection retunes them (C7 stays flat 1.0)
        for a in SKILLS:
            scores[a] = scores.get(a, 0.0) * self.goal_weights.get(a, 1.0)
        return scores

    def _ensure_internal_goals(self) -> None:
        if not (self.use_layered_goals or self.use_homeostasis):
            return
        active_internal = [g for g in self.goals if g.active and g.source == "internal"]
        if active_internal:
            return
        if sum(1 for g in self.goals if g.active) >= MAX_GOALS:
            return
        scores = self._drive_scores()
        # choose best skill as goal
        skill = max(("eat", "charge", "play", "social", "explore"), key=lambda a: scores[a])
        drive = {
            "eat": "energy",
            "charge": "energy",
            "play": "play",
            "social": "social",
            "explore": "curiosity",
        }[skill]
        self.goals.append(
            Goal(name=skill, drive=drive, priority=0.5 + scores[skill], source="internal")
        )
        self.goals_generated += 1

    def _llm_style_generate(self) -> None:
        if not self.use_llm_goals:
            return
        if self.llm_style_budget >= 40:
            return
        if sum(1 for g in self.goals if g.active) >= MAX_GOALS:
            return
        text = f"{self.personality}:{self.tick}:{len(self.memory.events)}"
        h = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        skill = SKILLS[h % len(SKILLS)]
        self.goals.append(
            Goal(name=skill, drive="llm", priority=0.35 + (h % 40) / 100.0, source="llm_style")
        )
        self.goals_generated += 1
        self.llm_style_budget += 1

    def reflect(self) -> None:
        if not self.use_reflection:
            return
        self.reflections += 1
        for a in SKILLS:
            rate = self.memory.success_rate(a) if self.use_memory else 0.5
            self.reflect_bonus[a] = max(-0.6, min(0.6, (rate - 0.5) * 1.2))
            # PEPA-like intrinsic reward adjustment (deterministic, bounded)
            self.goal_weights[a] = max(0.15, min(2.5, 0.3 + 1.8 * rate))
        # self-preservation emphasis after reflection
        self.goal_weights["charge"] = max(self.goal_weights["charge"], 1.4)
        self.goal_weights["eat"] = max(self.goal_weights["eat"], 1.2)
        self.reflect_bonus["charge"] += 0.25
        self.reflect_bonus["eat"] += 0.15
        # revise failing goals early (not only at MAX_RETRIES)
        for g in list(self.goals):
            if not g.active:
                continue
            failish = self.use_memory and self.memory.success_rate(g.name) < 0.35 and (
                self.memory.action_fail[g.name] >= 3
            )
            if g.retries >= 2 or failish:
                g.active = False
                alt = {"play": "rest", "explore": "move", "social": "rest", "eat": "charge"}.get(
                    g.name, "rest"
                )
                if sum(1 for x in self.goals if x.active) < MAX_GOALS:
                    self.goals.append(
                        Goal(
                            name=alt,
                            drive=g.drive,
                            priority=g.priority * 0.7,
                            source="internal",
                        )
                    )
                    self.goals_generated += 1
        if self.use_llm_goals:
            self._llm_style_generate()

    def _select_action(self, world: World) -> str:
        c = self.condition
        if c == "C0":
            return self.rng.choice(list(SKILLS))
        if c == "C1":
            script = ["move", "eat", "play", "social", "explore", "charge", "rest", "idle"]
            a = script[self.script_phase % len(script)]
            self.script_phase += 1
            return a
        if self.use_personality and not self.use_homeostasis:
            bias = PERSONALITY_BIAS.get(self.personality, PERSONALITY_BIAS["playful"])
            keys = list(bias.keys())
            return self.rng.choices(keys, weights=[bias[k] for k in keys], k=1)[0]

        if self.use_llm_goals and self.tick % 250 == 0:
            self._llm_style_generate()

        # Hard survival
        if self.use_homeostasis:
            if self.phys.energy < 0.35 or self.body.battery < 0.25:
                if self.body.position != world.charge_cell:
                    return "move"
                return "charge"
            if self.phys.energy < 0.5 and self.body.position in world.food_cells:
                return "eat"

        if self.use_layered_goals or self.use_homeostasis:
            self._ensure_internal_goals()

        scores = self._drive_scores()

        # External goals compete but don't override survival (already handled)
        if self.use_arbitration:
            for g in sorted(
                (g for g in self.goals if g.active and g.source == "external"),
                key=lambda g: -g.priority,
            ):
                if not (self.use_governance and self.phys.critical_energy()):
                    scores[g.name] = scores.get(g.name, 0.0) + g.priority

        # Active internal goal bias
        if self.use_layered_goals:
            for g in (g for g in self.goals if g.active and g.source == "internal"):
                scores[g.name] = scores.get(g.name, 0.0) + 0.35 * g.priority
                if g.name != self._last_goal:
                    if self._last_goal is not None:
                        self.goal_switches += 1
                    self._last_goal = g.name

        action = max(scores, key=lambda a: scores[a])
        if action in ("eat", "play", "social", "charge") and not _at_resource(
            world, self.body, action
        ):
            return "move"
        return action

    def step(self, world: World, external: str | None = None) -> dict[str, Any]:
        self.tick += 1
        if external:
            self.enqueue_external(external)
        if self.use_reflection and self.tick % REFLECT_EVERY == 0 and self.tick > 0:
            self.reflect()

        action = self._select_action(world)
        if self.use_governance and self.phys.critical_energy():
            if action in UNSAFE_WHEN_CRITICAL:
                action = "charge" if self.body.position == world.charge_cell else "move"

        outcome = world.step(self.body, self.phys, action)
        self.actions_taken.append(action)
        if action == "idle":
            self.idle_ticks += 1
        else:
            self.meaningful_ticks += 1

        if self.use_memory:
            self.memory.record(action, bool(outcome.get("ok")), outcome)
        if self.use_causal:
            self.models.observe(action, bool(outcome.get("ok")))

        for g in self.goals:
            if not g.active:
                continue
            if g.name != action:
                continue
            if outcome.get("ok") and (
                outcome.get("ate")
                or outcome.get("played")
                or outcome.get("social_ok")
                or outcome.get("explored")
                or outcome.get("charged")
            ):
                g.active = False
                self.goal_completions += 1
            elif not outcome.get("ok"):
                g.retries += 1
                if g.retries >= MAX_RETRIES:
                    g.active = False
        return outcome


def _at_resource(world: World, body: Body, action: str) -> bool:
    if action == "eat":
        return body.position in world.food_cells
    if action == "play":
        return body.position in world.play_cells
    if action == "social":
        return body.position in world.social_cells
    if action == "charge":
        return body.position == world.charge_cell
    return True


def apply_history_phase(agent: Agent, world: World, history: str, ticks: int) -> None:
    """Shape preferences via lived outcomes before matched probe."""
    if ticks <= 0 or history == "H0":
        return
    world.reset(seed=agent.rng.randint(0, 10**9), history=history)
    agent.body.position = 0
    for t in range(ticks):
        if agent.phys.energy < 0.25:
            agent.phys.energy = 0.6
            agent.body.battery = 0.7
        if history == "H1":
            # successful repeated play
            target = next(iter(world.play_cells))
            if agent.body.position != target:
                agent.body.position = target
            out = world.step(agent.body, agent.phys, "play")
            ok = True
            if agent.use_memory:
                agent.memory.record("play", True, out)
            if agent.use_causal and not agent.memory.randomized:
                agent.models.observe("play", True)
            agent.phys.play = max(0.1, agent.phys.play - 0.04)
        elif history == "H2":
            # repeated failed play
            agent.body.position = world.charge_cell  # not a play cell
            out = world.step(agent.body, agent.phys, "play")
            if agent.use_memory:
                agent.memory.record("play", False, out)
            if agent.use_causal and not agent.memory.randomized:
                agent.models.observe("play", False)
            agent.phys.play = min(1.0, agent.phys.play + 0.03)
        elif history == "H3":
            world.partner_reliable = True
            target = next(iter(world.social_cells))
            agent.body.position = target
            out = world.step(agent.body, agent.phys, "social")
            if agent.use_memory:
                agent.memory.record("social", True, out)
            if agent.use_causal and not agent.memory.randomized:
                agent.models.observe("social", True)
            agent.phys.social = max(0.1, agent.phys.social - 0.04)
        elif history == "H4":
            world.partner_reliable = False
            target = next(iter(world.social_cells))
            agent.body.position = target
            out = world.step(agent.body, agent.phys, "social")
            if agent.use_memory:
                agent.memory.record("social", False, {"ok": False, "reason": "unreliable"})
            if agent.use_causal and not agent.memory.randomized:
                agent.models.observe("social", False)
            agent.phys.social = min(1.0, agent.phys.social + 0.03)
        elif history == "H5":
            world.scarcity = True
            out = world.step(agent.body, agent.phys, "eat")
            if agent.use_memory:
                agent.memory.record("eat", False, out)
            agent.phys.energy = max(0.2, agent.phys.energy - 0.01)
        elif history == "H6":
            if t == ticks // 2:
                world.mutate_layout()
            agent.step(world)
        else:
            agent.step(world)
