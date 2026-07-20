"""Interruptible bounded planning + priority scheduling (independent contracts)."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from models import MAX_COMPOSITION_NODES, MAX_PLAN_DEPTH, ModelStore
from environment import ACTIONS, World


@dataclass
class PlanStep:
    action: str
    expected_outcome: str
    model_id: str | None = None


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    interrupted: bool = False
    completed: bool = False


@dataclass
class GoalItem:
    goal: str
    priority: float
    source: str = "task"  # task|homeostasis


class PriorityQueue:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._items: list[GoalItem] = []

    def push(self, goal: str, priority: float, source: str = "task") -> None:
        self._items.append(GoalItem(goal, priority, source))
        if self.enabled:
            self._items.sort(key=lambda g: g.priority, reverse=True)

    def pop(self) -> GoalItem | None:
        if not self._items:
            return None
        if self.enabled:
            return self._items.pop(0)
        return self._items.pop(0)  # FIFO if disabled still pops first inserted if unsorted

    def clear(self) -> None:
        self._items.clear()


class Planner:
    def __init__(
        self,
        store: ModelStore,
        *,
        use_inverse: bool = True,
        use_composition: bool = True,
        use_priority: bool = True,
        randomized: bool = False,
        max_depth: int = MAX_PLAN_DEPTH,
        seed: int = 0,
    ):
        self.store = store
        self.use_inverse = use_inverse
        self.use_composition = use_composition
        self.randomized = randomized
        self.max_depth = max_depth
        self.rng = random.Random(seed)
        self.goals = PriorityQueue(enabled=use_priority)
        self.active_plan: Plan | None = None
        self.replans = 0
        self.interruptions = 0

    def enqueue_goal(self, goal: str, priority: float, source: str = "task") -> None:
        self.goals.push(goal, priority, source)

    def compose_plan(self, goal_outcome: str, features: tuple[str, ...]) -> Plan:
        """Bounded BFS over inverse models to reach desired outcome."""
        plan = Plan(goal=goal_outcome)
        if not self.use_inverse:
            # Random thrashing
            plan.steps = [
                PlanStep(action=self.rng.choice(ACTIONS), expected_outcome="?")
                for _ in range(2)
            ]
            return plan

        if not self.use_composition:
            cands = self.store.inverse(
                goal_outcome, features, randomized=self.randomized, rng=self.rng
            )
            if cands:
                m = cands[0]
                plan.steps = [
                    PlanStep(action=m.action, expected_outcome=m.outcome, model_id=m.model_id)
                ]
            return plan

        # BFS: find chain of models ending at goal
        # Node = (current_needed_outcome, path_reversed)
        frontier: deque[tuple[str, list[PlanStep]]] = deque([(goal_outcome, [])])
        visited = {goal_outcome}
        nodes = 0
        found: list[PlanStep] | None = None
        while frontier and nodes < MAX_COMPOSITION_NODES:
            need, path = frontier.popleft()
            nodes += 1
            if len(path) >= self.max_depth:
                continue
            # Do not filter by current features here — missing near:* becomes a subgoal
            cands = self.store.inverse(need, None, randomized=self.randomized, rng=self.rng)
            if not cands:
                continue
            for m in cands[:5]:
                step = PlanStep(action=m.action, expected_outcome=m.outcome, model_id=m.model_id)
                new_path = path + [step] if False else [step] + path
                missing = [
                    f for f in m.context_features if f.startswith("near:") and f not in features
                ]
                if not missing and len(new_path) <= self.max_depth:
                    found = new_path
                    break
                for feat in missing:
                    obj = feat.split(":", 1)[1]
                    pre = f"near_{obj}"
                    approach = PlanStep(action=f"approach_{obj}", expected_outcome=pre)
                    candidate = [approach, step] + path
                    if pre not in visited and len(candidate) <= self.max_depth:
                        visited.add(pre)
                        # Also try completing once approach is assumed
                        found = candidate
                        break
                if found:
                    break
            if found:
                break
        if found:
            plan.steps = found
        elif self.use_inverse:
            cands = self.store.inverse(
                goal_outcome, None, randomized=self.randomized, rng=self.rng
            )
            if cands:
                m = cands[0]
                steps = [
                    PlanStep(action=m.action, expected_outcome=m.outcome, model_id=m.model_id)
                ]
                for feat in m.context_features:
                    if feat.startswith("near:") and feat not in features:
                        obj = feat.split(":", 1)[1]
                        steps.insert(0, PlanStep(action=f"approach_{obj}", expected_outcome=f"near_{obj}"))
                plan.steps = steps[: self.max_depth]
        return plan

    def act(self, world: World, learn: bool = True) -> str:
        obs = world.observe()
        features = obs["features"]

        if self.active_plan is None or self.active_plan.completed or self.active_plan.interrupted:
            item = self.goals.pop()
            if item is None:
                return "wait"
            self.active_plan = self.compose_plan(item.goal, features)

        plan = self.active_plan
        assert plan is not None
        if not plan.steps:
            plan.completed = True
            return "wait"

        step = plan.steps[0]
        pred_out, pred_cfd = self.store.predict(features, step.action)
        before = features
        obs2, outcome, _ = world.step(step.action)
        after = obs2["features"]

        # Always resolve delayed outcomes in the body
        if outcome == "grab_pending":
            obs3, outcome, _ = world.step("wait")
            after = obs3["features"]

        if learn:
            learn_feats = tuple(
                f for f in before if not f.startswith("rule_v:") and not f.startswith("holding:")
            )
            if step.action == "grab":
                learn_feats = tuple(f for f in learn_feats if f.startswith("near:"))
            if outcome not in ("waited", "grab_pending", "noop"):
                self.store.observe(learn_feats, step.action, outcome)

        # Interrupt if prediction fails (when we had one)
        expected = step.expected_outcome
        if expected not in ("?", outcome) and pred_out is not None and pred_out != outcome:
            plan.interrupted = True
            self.interruptions += 1
            self.replans += 1
            # Replan remaining toward same goal
            self.goals.push(plan.goal, priority=1.0, source="replan")
            self.active_plan = None
            return step.action

        plan.steps.pop(0)
        if not plan.steps:
            plan.completed = True
        return step.action


def babble_episode(world: World, store: ModelStore, seed: int, steps: int = 40) -> None:
    """Structured motor babbling (AERA-like cmd streams) to populate forward models.

    Not seed-supplied causal models — only experience. Biases approach→grab→wait
    sequences so delayed outcomes are observed often enough to learn.
    """
    rng = random.Random(seed)
    world.reset(seed)
    script = []
    for obj in ("sphere", "cube", "distractor"):
        script.extend([f"approach_{obj}", "grab", "wait", "release", "wait"])
    # Fill remaining with noise
    while len(script) < steps:
        script.append(rng.choice(ACTIONS))
    rng.shuffle(script)
    # Ensure some intact approach-grab-wait triples survive
    for obj in ("sphere", "cube"):
        script = [f"approach_{obj}", "grab", "wait", "release"] + script

    for action in script[:steps]:
        before = tuple(f for f in world.observe()["features"] if not f.startswith("rule_v:"))
        holding = world.holding
        causal = tuple(f for f in before if f.startswith("near:"))
        _, outcome, _ = world.step(action)
        if outcome == "grab_pending":
            _, outcome, _ = world.step("wait")
        if action == "grab":
            if holding is not None:
                continue  # don't pollute near→grab models while already holding
            if outcome in ("waited", "grab_pending", "noop"):
                continue
            store.observe(causal, action, outcome)
        else:
            learn_ctx = tuple(f for f in before if not f.startswith("holding:"))
            store.observe(learn_ctx, action, outcome)
