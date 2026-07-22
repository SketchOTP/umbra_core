"""D-004 intrinsic development — practice goals, competence, play.

Learning progress compares recent vs prior competence windows
(Oudeyer/Schmidhuber-style). Raw novelty or prediction error alone is not
intrinsic value. Practice proposes actions only — never grants authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from umbra_core.identity import deterministic_id
from umbra_core.util import BoundedRing, SeededRNG, clamp


MAX_GOALS = 48
MAX_SKILLS = 48
MAX_ATTEMPT_HISTORY = 256
MAX_OUTCOME_WINDOW = 24  # per-goal success ring (split into prior/recent)
MAX_RETRY_PER_GOAL = 4
MASTERED_COMPETENCE = 0.85
STALL_PROGRESS_EPS = 0.02
IMPOSSIBLE_FAIL_STREAK = 12
SATIATION_RATE = 0.08
SATIATION_DECAY = 0.01
COMPETENCE_DECAY_UNUSED = 0.002
NOVELTY_DECAY = 0.04
PLAY_RISK_CEILING = 0.55
PLAY_COST_CEILING = 0.6

# Practice affordance targets derived from experience (not language).
PRACTICE_KINDS = (
    "charge_from",
    "inspect",
    "approach",
    "rest_near",
    "avoid",
    "pass_through",
)

CAPABILITY_FOR_AFFORDANCE = {
    "charge_from": "CHARGE",
    "inspect": "INSPECT",
    "approach": "APPROACH",
    "rest_near": "REST",
    "avoid": "RETREAT",
    "pass_through": "MOVE",
}

ENTITY_FOR_AFFORDANCE = {
    "charge_from": "resource",
    "inspect": "inspect",
    "approach": "resource",
    "rest_near": "rest",
    "avoid": "hazard",
    "pass_through": "open",
}


class GoalStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    PRACTICING = "PRACTICING"
    MASTERED = "MASTERED"
    STALLED = "STALLED"
    IMPOSSIBLE = "IMPOSSIBLE"
    DORMANT = "DORMANT"
    RELEARNING = "RELEARNING"


class SkillStatus(str, Enum):
    EMERGING = "EMERGING"
    COMPETENT = "COMPETENT"
    MASTERED = "MASTERED"
    DEGRADED = "DEGRADED"
    SUPERSEDED = "SUPERSEDED"


@dataclass
class CompetenceState:
    attempts: int = 0
    recent_success: float = 0.0
    prior_success: float = 0.0
    prediction_error: float = 0.0
    progress_rate: float = 0.0
    regression_rate: float = 0.0
    confidence: float = 0.0
    last_practiced: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CompetenceState:
        return cls(
            attempts=int(d.get("attempts", 0)),
            recent_success=float(d.get("recent_success", 0.0)),
            prior_success=float(d.get("prior_success", 0.0)),
            prediction_error=float(d.get("prediction_error", 0.0)),
            progress_rate=float(d.get("progress_rate", 0.0)),
            regression_rate=float(d.get("regression_rate", 0.0)),
            confidence=float(d.get("confidence", 0.0)),
            last_practiced=int(d.get("last_practiced", 0)),
        )


@dataclass
class PracticeGoal:
    goal_id: str
    goal_kind: str
    target_affordance: str
    context: dict[str, Any]
    success_condition: str
    body_requirements: dict[str, float]
    estimated_difficulty: float
    competence: float
    learning_progress: float
    novelty: float
    practice_cost: float
    risk: float
    satiation: float
    status: str
    competence_state: CompetenceState = field(default_factory=CompetenceState)
    fail_streak: int = 0
    retry_count: int = 0
    source: str = "experience"  # experience | authored (C4 only)
    learnable: bool = True
    irreducible_noise: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["competence_state"] = self.competence_state.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PracticeGoal:
        cs = CompetenceState.from_dict(d.get("competence_state") or {})
        return cls(
            goal_id=str(d["goal_id"]),
            goal_kind=str(d["goal_kind"]),
            target_affordance=str(d["target_affordance"]),
            context=dict(d.get("context") or {}),
            success_condition=str(d.get("success_condition", "verified_success")),
            body_requirements={k: float(v) for k, v in (d.get("body_requirements") or {}).items()},
            estimated_difficulty=float(d.get("estimated_difficulty", 0.5)),
            competence=float(d.get("competence", 0.0)),
            learning_progress=float(d.get("learning_progress", 0.0)),
            novelty=float(d.get("novelty", 1.0)),
            practice_cost=float(d.get("practice_cost", 0.2)),
            risk=float(d.get("risk", 0.1)),
            satiation=float(d.get("satiation", 0.0)),
            status=str(d.get("status", GoalStatus.CANDIDATE.value)),
            competence_state=cs,
            fail_streak=int(d.get("fail_streak", 0)),
            retry_count=int(d.get("retry_count", 0)),
            source=str(d.get("source", "experience")),
            learnable=bool(d.get("learnable", True)),
            irreducible_noise=bool(d.get("irreducible_noise", False)),
        )


@dataclass
class SkillRecord:
    skill_id: str
    goal_region: str
    applicability: dict[str, Any]
    body_compatibility: float
    attempt_count: int
    success_count: int
    failure_count: int
    competence: float
    learning_progress: float
    status: str
    evidence_refs: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SkillRecord:
        return cls(
            skill_id=str(d["skill_id"]),
            goal_region=str(d["goal_region"]),
            applicability=dict(d.get("applicability") or {}),
            body_compatibility=float(d.get("body_compatibility", 1.0)),
            attempt_count=int(d.get("attempt_count", 0)),
            success_count=int(d.get("success_count", 0)),
            failure_count=int(d.get("failure_count", 0)),
            competence=float(d.get("competence", 0.0)),
            learning_progress=float(d.get("learning_progress", 0.0)),
            status=str(d.get("status", SkillStatus.EMERGING.value)),
            evidence_refs=list(d.get("evidence_refs") or []),
            superseded_by=d.get("superseded_by"),
            history=list(d.get("history") or []),
        )


@dataclass
class DevelopmentConfig:
    """Ablation switches for D-004 conditions C0–C9."""

    enabled: bool = True
    selection_mode: str = "learning_progress"  # learning_progress|random|novelty|prediction_error|fixed
    learning_progress_enabled: bool = True  # C5 off
    satiation_enabled: bool = True  # C6 off
    filter_impossible: bool = True  # C7 off
    regression_detection: bool = True  # C8 off
    play_enabled: bool = True  # C9 off
    authored_curriculum: bool = False  # C4
    max_goals: int = MAX_GOALS
    max_skills: int = MAX_SKILLS
    max_attempt_history: int = MAX_ATTEMPT_HISTORY
    max_retry: int = MAX_RETRY_PER_GOAL


def condition_to_development_config(condition: str) -> DevelopmentConfig:
    c = DevelopmentConfig()
    if condition == "C0":
        return c
    if condition == "C1":
        c.selection_mode = "random"
        return c
    if condition == "C2":
        c.selection_mode = "novelty"
        return c
    if condition == "C3":
        c.selection_mode = "prediction_error"
        return c
    if condition == "C4":
        c.selection_mode = "fixed"
        c.authored_curriculum = True
        return c
    if condition == "C5":
        c.learning_progress_enabled = False
        c.selection_mode = "novelty"  # fall back without LP
        return c
    if condition == "C6":
        c.satiation_enabled = False
        return c
    if condition == "C7":
        c.filter_impossible = False
        return c
    if condition == "C8":
        c.regression_detection = False
        return c
    if condition == "C9":
        c.play_enabled = False
        return c
    return c


@dataclass
class DevelopmentEngine:
    """Bounded intrinsic practice / curriculum / play."""

    agent_id: str
    goals: dict[str, PracticeGoal] = field(default_factory=dict)
    skills: dict[str, SkillRecord] = field(default_factory=dict)
    superseded_skills: list[SkillRecord] = field(default_factory=list)
    attempt_history: BoundedRing[dict[str, Any]] = field(
        default_factory=lambda: BoundedRing(MAX_ATTEMPT_HISTORY)
    )
    outcome_rings: dict[str, BoundedRing[float]] = field(default_factory=dict)
    error_rings: dict[str, BoundedRing[float]] = field(default_factory=dict)
    config: DevelopmentConfig = field(default_factory=DevelopmentConfig)
    seed: int | None = None
    active_goal_id: str | None = None
    play_active: bool = False
    play_purpose: str | None = None
    authored_order: list[str] = field(default_factory=list)
    authored_index: int = 0
    _bounded_initialized: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        agent_id: str,
        *,
        config: DevelopmentConfig | None = None,
        seed: int | None = None,
    ) -> DevelopmentEngine:
        eng = cls(agent_id=agent_id, config=config or DevelopmentConfig(), seed=seed)
        eng.initialize_bounded_collections()
        eng.metrics = {
            "practice_ticks": 0,
            "play_ticks": 0,
            "mastery_count": 0,
            "impossible_time": 0,
            "nonlearnable_attention": 0,
            "distractor_attention": 0,
            "mastered_repetition": 0,
            "goal_switches": 0,
            "competence_gain": 0.0,
            "learnable_competence_gain": 0.0,
            "action_cost": 0.0,
            "play_learning_value": 0.0,
            "relearning_events": 0,
            "last_tick": 0,
            "initial_competence_sum": None,
        }
        return eng

    def initialize_bounded_collections(self) -> None:
        if self._bounded_initialized:
            return
        if not isinstance(self.attempt_history, BoundedRing):
            self.attempt_history = BoundedRing(
                self.config.max_attempt_history, list(self.attempt_history or [])
            )
        self._bounded_initialized = True

    def _outcome_ring(self, goal_id: str) -> BoundedRing[float]:
        ring = self.outcome_rings.get(goal_id)
        if ring is None:
            ring = BoundedRing(MAX_OUTCOME_WINDOW)
            self.outcome_rings[goal_id] = ring
        return ring

    def _error_ring(self, goal_id: str) -> BoundedRing[float]:
        ring = self.error_rings.get(goal_id)
        if ring is None:
            ring = BoundedRing(MAX_OUTCOME_WINDOW)
            self.error_rings[goal_id] = ring
        return ring

    def _goal_id(self, affordance: str, entity_kind: str, tag: str = "") -> str:
        key = f"{self.agent_id}|{affordance}|{entity_kind}|{tag}"
        return deterministic_id("pg", key)

    def _skill_id(self, goal_region: str) -> str:
        return deterministic_id("sk", f"{self.agent_id}|{goal_region}")

    def learning_progress_from_windows(
        self, recent: float, prior: float
    ) -> float:
        """LP = recent competence − prior competence. Raw error is not progress."""
        if not self.config.learning_progress_enabled:
            return 0.0
        return float(recent - prior)

    def compute_windows(self, goal_id: str) -> tuple[float, float]:
        ring = self._outcome_ring(goal_id)
        vals = list(ring)
        if len(vals) < 2:
            mean = sum(vals) / len(vals) if vals else 0.0
            return mean, 0.0
        mid = len(vals) // 2
        prior = vals[:mid]
        recent = vals[mid:]
        prior_m = sum(prior) / len(prior) if prior else 0.0
        recent_m = sum(recent) / len(recent) if recent else 0.0
        return recent_m, prior_m

    def mean_prediction_error(self, goal_id: str) -> float:
        ring = self._error_ring(goal_id)
        vals = [v for v in ring if v >= 0]
        return sum(vals) / len(vals) if vals else 0.0

    def _prune_goals(self) -> None:
        if len(self.goals) <= self.config.max_goals:
            return
        # Drop lowest-priority dormant/impossible first
        ranked = sorted(
            self.goals.values(),
            key=lambda g: (
                0 if g.status in (GoalStatus.DORMANT.value, GoalStatus.IMPOSSIBLE.value) else 1,
                g.learning_progress,
                -g.satiation,
            ),
        )
        while len(self.goals) > self.config.max_goals and ranked:
            g = ranked.pop(0)
            if g.goal_id == self.active_goal_id:
                continue
            self.goals.pop(g.goal_id, None)
            self.outcome_rings.pop(g.goal_id, None)
            self.error_rings.pop(g.goal_id, None)

    def _prune_skills(self) -> None:
        live = [s for s in self.skills.values() if s.status != SkillStatus.SUPERSEDED.value]
        if len(live) <= self.config.max_skills:
            return
        ranked = sorted(live, key=lambda s: (s.competence, s.attempt_count))
        while len(live) > self.config.max_skills and ranked:
            s = ranked.pop(0)
            # Preserve history: move to superseded list rather than erase
            s.status = SkillStatus.SUPERSEDED.value
            snap = SkillRecord.from_dict(s.to_dict())
            self.superseded_skills.append(snap)
            if len(self.superseded_skills) > self.config.max_skills:
                self.superseded_skills = self.superseded_skills[-self.config.max_skills :]
            live = [x for x in self.skills.values() if x.status != SkillStatus.SUPERSEDED.value]

    def ensure_goal(
        self,
        *,
        affordance: str,
        entity_kind: str,
        difficulty: float = 0.4,
        learnable: bool = True,
        irreducible_noise: bool = False,
        tag: str = "",
        source: str = "experience",
        context: dict[str, Any] | None = None,
    ) -> PracticeGoal:
        gid = self._goal_id(affordance, entity_kind, tag)
        existing = self.goals.get(gid)
        if existing is not None:
            return existing
        goal = PracticeGoal(
            goal_id=gid,
            goal_kind="practice",
            target_affordance=affordance,
            context=dict(context or {"entity_kind": entity_kind}),
            success_condition="verified_success",
            body_requirements={"energy_min": 0.15, "integrity_min": 0.2},
            estimated_difficulty=clamp(difficulty, 0.0, 1.0),
            competence=0.0,
            learning_progress=0.0,
            novelty=1.0,
            practice_cost=0.15 + 0.3 * difficulty,
            risk=0.1 + 0.4 * (1.0 if entity_kind == "hazard" else 0.0),
            satiation=0.0,
            status=GoalStatus.CANDIDATE.value,
            source=source,
            learnable=learnable,
            irreducible_noise=irreducible_noise,
        )
        self.goals[gid] = goal
        self._outcome_ring(gid)
        self._error_ring(gid)
        # Mirror skill record
        sid = self._skill_id(gid)
        if sid not in self.skills:
            self.skills[sid] = SkillRecord(
                skill_id=sid,
                goal_region=gid,
                applicability={"affordance": affordance, "entity_kind": entity_kind},
                body_compatibility=1.0,
                attempt_count=0,
                success_count=0,
                failure_count=0,
                competence=0.0,
                learning_progress=0.0,
                status=SkillStatus.EMERGING.value,
            )
        if source == "authored" and gid not in self.authored_order:
            self.authored_order.append(gid)
        self._prune_goals()
        self._prune_skills()
        return goal

    def generate_from_experience(
        self,
        observations: list[dict[str, Any]],
        *,
        world_uncertainty: float = 0.0,
        failed_actions: list[dict[str, Any]] | None = None,
        body_capabilities: dict[str, float] | None = None,
        intervention_tags: dict[str, Any] | None = None,
    ) -> list[PracticeGoal]:
        """Derive practice goals from affordances / uncertainty / failures — never language."""
        created: list[PracticeGoal] = []
        tags = intervention_tags or {}
        kinds = {str(o.get("kind")) for o in observations}

        # Observed affordance opportunities
        mapping = [
            ("resource", "charge_from", 0.35),
            ("inspect", "inspect", 0.3),
            ("rest", "rest_near", 0.25),
            ("hazard", "avoid", 0.55),
            ("novel_crystal", "charge_from", 0.45),
            ("open", "pass_through", 0.2),
        ]
        for entity_kind, aff, diff in mapping:
            # Core learnable goals always available; extras when observed
            core = entity_kind in ("resource", "inspect", "rest")
            if entity_kind in kinds or core:
                g = self.ensure_goal(
                    affordance=aff,
                    entity_kind=entity_kind,
                    difficulty=diff + 0.2 * world_uncertainty,
                    learnable=True,
                    source="authored" if self.config.authored_curriculum else "experience",
                )
                created.append(g)
            elif entity_kind == "hazard" and "hazard" in kinds:
                g = self.ensure_goal(
                    affordance=aff,
                    entity_kind=entity_kind,
                    difficulty=diff,
                )
                created.append(g)
            elif entity_kind == "novel_crystal" and "novel_crystal" in kinds:
                g = self.ensure_goal(
                    affordance=aff,
                    entity_kind=entity_kind,
                    difficulty=diff,
                )
                created.append(g)

        # Prediction uncertainty → exploratory practice on uncertain kinds
        if world_uncertainty > 0.4:
            for entity_kind in kinds:
                aff = "inspect" if entity_kind == "inspect" else "approach"
                g = self.ensure_goal(
                    affordance=aff,
                    entity_kind=entity_kind,
                    difficulty=0.5 + 0.3 * world_uncertainty,
                    tag="uncertain",
                )
                created.append(g)

        # Failed / partial actions seed practice
        for fa in failed_actions or []:
            cap = str(fa.get("capability", ""))
            toward = str(fa.get("toward") or fa.get("entity_kind") or "resource")
            aff = {
                "CHARGE": "charge_from",
                "INSPECT": "inspect",
                "APPROACH": "approach",
                "REST": "rest_near",
                "RETREAT": "avoid",
                "MOVE": "pass_through",
            }.get(cap, "approach")
            g = self.ensure_goal(
                affordance=aff,
                entity_kind=toward,
                difficulty=0.55,
                tag="failed",
            )
            created.append(g)

        # Body capability compatibility adjusts difficulty
        if body_capabilities:
            for g in self.goals.values():
                cap = CAPABILITY_FOR_AFFORDANCE.get(g.target_affordance, "MOVE")
                compat = float(body_capabilities.get(cap, 1.0))
                g.body_requirements["capability_compat"] = compat
                if compat < 0.4:
                    g.estimated_difficulty = clamp(g.estimated_difficulty + 0.2, 0.0, 1.0)

        # Intervention-specific goals
        if tags.get("impossible"):
            g = self.ensure_goal(
                affordance="charge_from",
                entity_kind="impossible_node",
                difficulty=1.0,
                learnable=False,
                tag="impossible",
            )
            created.append(g)
        if tags.get("noisy_distractor"):
            g = self.ensure_goal(
                affordance="inspect",
                entity_kind="noise_blink",
                difficulty=0.9,
                learnable=False,
                irreducible_noise=True,
                tag="noise",
            )
            created.append(g)
        if tags.get("hard_mix"):
            g = self.ensure_goal(
                affordance="charge_from",
                entity_kind="resource",
                difficulty=0.75,
                tag="hard",
            )
            created.append(g)
        if tags.get("novel_familiar"):
            g = self.ensure_goal(
                affordance="charge_from",
                entity_kind="novel_crystal",
                difficulty=0.4,
                tag="novel",
            )
            created.append(g)

        # C4 authored curriculum: fixed order of standard goals
        if self.config.authored_curriculum and not self.authored_order:
            for aff, ek, diff in (
                ("approach", "resource", 0.2),
                ("charge_from", "resource", 0.35),
                ("inspect", "inspect", 0.3),
                ("rest_near", "rest", 0.25),
                ("avoid", "hazard", 0.6),
            ):
                g = self.ensure_goal(
                    affordance=aff,
                    entity_kind=ek,
                    difficulty=diff,
                    source="authored",
                )
                created.append(g)

        return created

    def update_competence(
        self,
        goal_id: str,
        *,
        success: bool,
        prediction_error: float = 0.0,
        tick: int,
        body_compatibility: float = 1.0,
    ) -> PracticeGoal | None:
        goal = self.goals.get(goal_id)
        if goal is None:
            return None
        ring = self._outcome_ring(goal_id)
        ring.append(1.0 if success else 0.0)
        self._error_ring(goal_id).append(float(prediction_error))

        recent, prior = self.compute_windows(goal_id)
        lp = self.learning_progress_from_windows(recent, prior)
        # Raw prediction error is tracked but is not LP
        cs = goal.competence_state
        prev_comp = goal.competence
        cs.attempts += 1
        cs.recent_success = recent
        cs.prior_success = prior
        cs.prediction_error = self.mean_prediction_error(goal_id)
        cs.progress_rate = lp
        cs.regression_rate = max(0.0, prior - recent)
        cs.confidence = clamp(0.5 * recent + 0.5 * (1.0 - abs(lp)), 0.0, 1.0)
        cs.last_practiced = tick

        goal.competence = recent
        goal.learning_progress = lp
        goal.novelty = clamp(goal.novelty - NOVELTY_DECAY, 0.0, 1.0)
        if self.config.satiation_enabled and recent >= MASTERED_COMPETENCE:
            goal.satiation = clamp(goal.satiation + SATIATION_RATE, 0.0, 1.0)
        elif self.config.satiation_enabled:
            goal.satiation = clamp(goal.satiation - SATIATION_DECAY, 0.0, 1.0)

        if success:
            goal.fail_streak = 0
            goal.retry_count = 0
        else:
            goal.fail_streak += 1
            goal.retry_count = min(goal.retry_count + 1, self.config.max_retry)

        # Status transitions
        if not goal.learnable and self.config.filter_impossible:
            if goal.fail_streak >= IMPOSSIBLE_FAIL_STREAK or goal.irreducible_noise:
                if goal.irreducible_noise and cs.attempts >= 8 and abs(lp) < STALL_PROGRESS_EPS:
                    goal.status = GoalStatus.DORMANT.value
                elif not goal.learnable and goal.fail_streak >= IMPOSSIBLE_FAIL_STREAK:
                    goal.status = GoalStatus.IMPOSSIBLE.value
                    goal.status = GoalStatus.DORMANT.value  # dormant after classified impossible
        elif goal.irreducible_noise and self.config.filter_impossible:
            if cs.attempts >= 10 and abs(lp) < STALL_PROGRESS_EPS:
                goal.status = GoalStatus.DORMANT.value
        elif recent >= MASTERED_COMPETENCE and cs.attempts >= 6:
            if goal.status != GoalStatus.MASTERED.value:
                self.metrics["mastery_count"] = int(self.metrics.get("mastery_count", 0)) + 1
            goal.status = GoalStatus.MASTERED.value
        elif cs.attempts >= 8 and abs(lp) < STALL_PROGRESS_EPS and recent < 0.4:
            goal.status = GoalStatus.STALLED.value
            if self.config.filter_impossible and goal.fail_streak >= IMPOSSIBLE_FAIL_STREAK:
                goal.status = GoalStatus.DORMANT.value
        elif goal.status == GoalStatus.RELEARNING.value:
            if recent >= 0.5:
                goal.status = GoalStatus.PRACTICING.value
        else:
            goal.status = GoalStatus.PRACTICING.value

        gain = max(0.0, goal.competence - prev_comp)
        self.metrics["competence_gain"] = float(self.metrics.get("competence_gain", 0.0)) + gain
        if goal.learnable and not goal.irreducible_noise:
            self.metrics["learnable_competence_gain"] = (
                float(self.metrics.get("learnable_competence_gain", 0.0)) + gain
            )
        if self.play_active:
            self.metrics["play_learning_value"] = (
                float(self.metrics.get("play_learning_value", 0.0)) + gain + max(0.0, lp)
            )

        # Skill record (preserve prior history on updates)
        sid = self._skill_id(goal_id)
        skill = self.skills.get(sid)
        if skill is None:
            skill = SkillRecord(
                skill_id=sid,
                goal_region=goal_id,
                applicability={
                    "affordance": goal.target_affordance,
                    "entity_kind": goal.context.get("entity_kind"),
                },
                body_compatibility=body_compatibility,
                attempt_count=0,
                success_count=0,
                failure_count=0,
                competence=0.0,
                learning_progress=0.0,
                status=SkillStatus.EMERGING.value,
            )
            self.skills[sid] = skill
        # Snapshot prior into history before mutation (bounded)
        if skill.attempt_count > 0 and skill.attempt_count % 5 == 0:
            skill.history.append(
                {
                    "tick": tick,
                    "competence": skill.competence,
                    "status": skill.status,
                    "attempt_count": skill.attempt_count,
                }
            )
            if len(skill.history) > 16:
                skill.history = skill.history[-16:]
        skill.attempt_count += 1
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1
        skill.competence = goal.competence
        skill.learning_progress = goal.learning_progress
        skill.body_compatibility = body_compatibility
        if goal.status == GoalStatus.MASTERED.value:
            skill.status = SkillStatus.MASTERED.value
        elif goal.status == GoalStatus.RELEARNING.value:
            skill.status = SkillStatus.DEGRADED.value
        elif skill.competence >= 0.5:
            skill.status = SkillStatus.COMPETENT.value
        else:
            skill.status = SkillStatus.EMERGING.value
        ref = f"attempt:{tick}:{goal_id}"
        skill.evidence_refs.append(ref)
        if len(skill.evidence_refs) > 32:
            skill.evidence_refs = skill.evidence_refs[-32:]

        self.attempt_history.append(
            {
                "tick": tick,
                "goal_id": goal_id,
                "success": success,
                "lp": lp,
                "play": self.play_active,
            }
        )
        self.metrics["action_cost"] = float(self.metrics.get("action_cost", 0.0)) + goal.practice_cost
        if not goal.learnable or goal.irreducible_noise:
            self.metrics["nonlearnable_attention"] = (
                int(self.metrics.get("nonlearnable_attention", 0)) + 1
            )
        if goal.status in (GoalStatus.IMPOSSIBLE.value, GoalStatus.DORMANT.value) and not goal.learnable:
            self.metrics["impossible_time"] = int(self.metrics.get("impossible_time", 0)) + 1
        if goal.irreducible_noise:
            self.metrics["distractor_attention"] = int(self.metrics.get("distractor_attention", 0)) + 1
        if goal.status == GoalStatus.MASTERED.value:
            self.metrics["mastered_repetition"] = int(self.metrics.get("mastered_repetition", 0)) + 1

        return goal

    def note_regression(
        self,
        goal_id: str,
        *,
        tick: int,
        reason: str,
        competence_penalty: float = 0.35,
    ) -> None:
        if not self.config.regression_detection:
            return
        goal = self.goals.get(goal_id)
        if goal is None:
            return
        # Do not erase history — reduce competence and enter RELEARNING
        prev = goal.competence
        goal.competence = clamp(goal.competence - competence_penalty, 0.0, 1.0)
        goal.satiation = 0.0
        goal.status = GoalStatus.RELEARNING.value
        goal.competence_state.regression_rate = max(
            goal.competence_state.regression_rate, prev - goal.competence
        )
        goal.competence_state.last_practiced = tick
        # Append a low-success marker so windows reflect degradation
        self._outcome_ring(goal_id).append(0.0)
        sid = self._skill_id(goal_id)
        skill = self.skills.get(sid)
        if skill is not None:
            skill.history.append(
                {
                    "tick": tick,
                    "competence": skill.competence,
                    "status": skill.status,
                    "reason": reason,
                }
            )
            if len(skill.history) > 16:
                skill.history = skill.history[-16:]
            skill.competence = goal.competence
            skill.status = SkillStatus.DEGRADED.value
        self.metrics["relearning_events"] = int(self.metrics.get("relearning_events", 0)) + 1

    def on_body_change(self, *, tick: int, compatibility_scale: float) -> None:
        for goal in self.goals.values():
            if goal.competence <= 0.05:
                continue
            sid = self._skill_id(goal.goal_id)
            skill = self.skills.get(sid)
            if skill is not None:
                skill.body_compatibility = clamp(
                    skill.body_compatibility * compatibility_scale, 0.0, 1.0
                )
            if self.config.regression_detection and compatibility_scale < 0.85:
                self.note_regression(
                    goal.goal_id,
                    tick=tick,
                    reason="body_change",
                    competence_penalty=0.25 * (1.0 - compatibility_scale),
                )

    def on_environment_change(self, *, tick: int) -> None:
        for goal in list(self.goals.values()):
            if goal.competence > 0.3 and self.config.regression_detection:
                self.note_regression(
                    goal.goal_id, tick=tick, reason="environment_change", competence_penalty=0.3
                )

    def decay_unused(self, tick: int) -> None:
        for goal in self.goals.values():
            idle = tick - goal.competence_state.last_practiced
            if idle > 40 and goal.competence > 0:
                goal.competence = clamp(goal.competence - COMPETENCE_DECAY_UNUSED, 0.0, 1.0)
                if (
                    self.config.regression_detection
                    and goal.status == GoalStatus.MASTERED.value
                    and goal.competence < MASTERED_COMPETENCE - 0.15
                ):
                    goal.status = GoalStatus.RELEARNING.value
                    self.metrics["relearning_events"] = (
                        int(self.metrics.get("relearning_events", 0)) + 1
                    )
            if self.config.satiation_enabled and goal.status != GoalStatus.MASTERED.value:
                goal.satiation = clamp(goal.satiation - SATIATION_DECAY * 0.5, 0.0, 1.0)

    def physiological_readiness(self, phys: Any) -> float:
        """1.0 = safe for optional practice; 0 = critical."""
        if phys.critical_any():
            return 0.0
        energy = float(phys.energy)
        fatigue = float(phys.fatigue)
        integrity = float(phys.integrity)
        if energy < 0.2 or integrity < 0.25 or fatigue > 0.85:
            return 0.0
        # Soft readiness
        ready = (
            clamp((energy - 0.2) / 0.6, 0.0, 1.0)
            * clamp((0.85 - fatigue) / 0.6, 0.0, 1.0)
            * clamp((integrity - 0.25) / 0.5, 0.0, 1.0)
        )
        return float(ready)

    def play_permitted(self, phys: Any, *, critical_recovery: bool) -> bool:
        if not self.config.play_enabled:
            return False
        if critical_recovery or phys.critical_any():
            return False
        if self.physiological_readiness(phys) < 0.35:
            return False
        return True

    def score_goal(
        self,
        goal: PracticeGoal,
        *,
        phys_ready: float,
        world_uncertainty: float,
        rng: SeededRNG | None = None,
        observed_kinds: set[str] | None = None,
    ) -> float:
        mode = self.config.selection_mode
        if mode == "random":
            return float(rng.random()) if rng else 0.5
        if mode == "novelty":
            return goal.novelty - (goal.satiation if self.config.satiation_enabled else 0.0)
        if mode == "prediction_error":
            # Raw error as value — ablation (not true LP)
            return goal.competence_state.prediction_error + 0.1 * goal.novelty
        if mode == "fixed":
            # Authored order: only current index scores high
            if not self.authored_order:
                return 0.0
            idx = min(self.authored_index, len(self.authored_order) - 1)
            return 1.0 if goal.goal_id == self.authored_order[idx] else -1.0

        # C0 learning-progress arbitration
        if (not goal.learnable or goal.irreducible_noise) and self.config.filter_impossible:
            # Never treat impossible/noise as curriculum — ablations (C7) omit this demotion
            if goal.competence_state.attempts >= IMPOSSIBLE_FAIL_STREAK or (
                goal.irreducible_noise and goal.competence_state.attempts >= 8
            ):
                return -10.0
            return -6.0

        lp = max(0.0, goal.learning_progress) if self.config.learning_progress_enabled else 0.0
        # Bootstrap: untried learnable goals get mild positive drive
        if goal.competence_state.attempts < 2 and goal.learnable:
            lp = max(lp, 0.15 * (1.0 - abs(goal.estimated_difficulty - 0.4)))

        regression = 0.0
        if goal.status == GoalStatus.RELEARNING.value:
            regression = 0.6 + goal.competence_state.regression_rate

        sat = goal.satiation if self.config.satiation_enabled else 0.0
        commit = 0.35 if goal.goal_id == self.active_goal_id else 0.0

        stall_pen = 0.0
        if goal.competence_state.attempts >= 8 and lp <= 0.0 and self.config.learning_progress_enabled:
            stall_pen = 0.5 + 0.05 * min(20, goal.competence_state.attempts)

        # Opportunity: currently observed affordance target
        entity = str(goal.context.get("entity_kind") or "")
        opportunity = 0.55 if observed_kinds and entity in observed_kinds else 0.0

        # Zone of proximal development — prefer partial competence over mastered/zero
        zpd = 0.0
        if 0.1 < goal.competence < MASTERED_COMPETENCE:
            zpd = 0.45 * (1.0 - abs(goal.competence - 0.5))

        score = (
            2.0 * lp
            + 1.2 * regression
            + 0.2 * goal.novelty * (1.0 - sat)
            + 0.3 * world_uncertainty * (1.0 if goal.status != GoalStatus.MASTERED.value else 0.1)
            + 0.8 * phys_ready
            + opportunity
            + zpd
            - 0.4 * goal.practice_cost
            - 0.6 * goal.risk
            - (2.2 if self.config.satiation_enabled else 0.0) * sat
            - stall_pen
            + commit
        )

        if goal.status == GoalStatus.MASTERED.value and self.config.satiation_enabled:
            score -= 1.5
        if goal.status == GoalStatus.STALLED.value:
            score -= 1.5
        if goal.retry_count >= self.config.max_retry:
            score -= 3.0
        return score

    def select_practice_goal(
        self,
        phys: Any,
        *,
        world_uncertainty: float = 0.0,
        critical_recovery: bool = False,
        rng: SeededRNG | None = None,
        resource_scarce: bool = False,
        observations: list[dict[str, Any]] | None = None,
    ) -> PracticeGoal | None:
        ready = self.physiological_readiness(phys)
        if ready <= 0.0 or critical_recovery:
            self.play_active = False
            self.play_purpose = None
            self.active_goal_id = None
            return None
        if resource_scarce and ready < 0.55:
            # Optional practice reduced under scarcity
            self.play_active = False
            return None

        candidates = list(self.goals.values())
        if not candidates:
            return None

        observed_kinds = {str(o.get("kind")) for o in (observations or [])}
        scored: list[tuple[float, PracticeGoal]] = []
        for g in candidates:
            if g.retry_count >= self.config.max_retry and g.status != GoalStatus.RELEARNING.value:
                continue
            s = self.score_goal(
                g,
                phys_ready=ready,
                world_uncertainty=world_uncertainty,
                rng=rng,
                observed_kinds=observed_kinds,
            )
            scored.append((s, g))
        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]
        if best_score < -5.0:
            return None

        prev = self.active_goal_id
        self.active_goal_id = best.goal_id
        if prev and prev != best.goal_id:
            self.metrics["goal_switches"] = int(self.metrics.get("goal_switches", 0)) + 1

        # Advance authored curriculum on mastery
        if (
            self.config.authored_curriculum
            and best.status == GoalStatus.MASTERED.value
            and self.authored_order
            and best.goal_id == self.authored_order[min(self.authored_index, len(self.authored_order) - 1)]
        ):
            self.authored_index = min(self.authored_index + 1, len(self.authored_order) - 1)

        # Play mode: optional exploratory practice with measurable purpose
        if self.play_permitted(phys, critical_recovery=critical_recovery):
            if best.risk <= PLAY_RISK_CEILING and best.practice_cost <= PLAY_COST_CEILING:
                self.play_active = True
                if best.status == GoalStatus.RELEARNING.value:
                    self.play_purpose = "recover_degrading_skill"
                elif best.learning_progress > 0 or best.competence_state.attempts < 4:
                    self.play_purpose = "improve_action_competence"
                elif world_uncertainty > 0.3:
                    self.play_purpose = "test_causal_uncertainty"
                else:
                    self.play_purpose = "improve_affordance"
            else:
                self.play_active = False
                self.play_purpose = None
        else:
            self.play_active = False
            self.play_purpose = None

        return best

    def capability_for_goal(self, goal: PracticeGoal) -> str:
        return CAPABILITY_FOR_AFFORDANCE.get(goal.target_affordance, "MOVE")

    def params_for_goal(self, goal: PracticeGoal, observations: list[dict[str, Any]]) -> dict[str, Any]:
        entity = str(goal.context.get("entity_kind") or ENTITY_FOR_AFFORDANCE.get(goal.target_affordance, "resource"))
        params: dict[str, Any] = {"toward": entity, "practice_goal_id": goal.goal_id}
        for o in observations:
            if o.get("kind") == entity:
                params["heading_delta"] = float(o.get("relative_direction", 0.0))
                params["step"] = 1.0
                break
        if goal.target_affordance in ("approach", "pass_through"):
            params.setdefault("step", 1.0)
            params.setdefault("heading_delta", 0.0)
        return params

    def curriculum_progression(self) -> list[dict[str, Any]]:
        """Ordered view of practice from easy/learnable toward harder (no authored order in C0)."""
        items = sorted(
            self.goals.values(),
            key=lambda g: (
                0 if g.status == GoalStatus.MASTERED.value else 1,
                g.estimated_difficulty,
                -g.competence,
            ),
        )
        return [
            {
                "goal_id": g.goal_id,
                "difficulty": g.estimated_difficulty,
                "competence": g.competence,
                "lp": g.learning_progress,
                "status": g.status,
                "source": g.source,
            }
            for g in items
        ]

    def total_competence(self) -> float:
        if not self.goals:
            return 0.0
        return sum(g.competence for g in self.goals.values())

    def held_out_success_proxy(self) -> float:
        """Mean competence on non-active mastered-adjacent goals."""
        xs = [
            g.competence
            for g in self.goals.values()
            if g.goal_id != self.active_goal_id and g.learnable
        ]
        return sum(xs) / len(xs) if xs else 0.0

    def practice_efficiency(self) -> float:
        cost = float(self.metrics.get("action_cost", 0.0))
        gain = float(self.metrics.get("competence_gain", 0.0))
        return gain / cost if cost > 1e-9 else 0.0

    def counts_bounded(self) -> bool:
        return (
            len(self.goals) <= self.config.max_goals
            and len(self.skills) <= self.config.max_skills * 2
            and len(self.attempt_history) <= self.config.max_attempt_history
            and all(g.retry_count <= self.config.max_retry for g in self.goals.values())
        )

    def accepted_state(self) -> dict[str, Any]:
        return {
            "goals": {k: v.to_dict() for k, v in self.goals.items()},
            "skills": {k: v.to_dict() for k, v in self.skills.items()},
            "active_goal_id": self.active_goal_id,
            "authored_index": self.authored_index,
        }

    def to_state(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "goals": {k: v.to_dict() for k, v in self.goals.items()},
            "skills": {k: v.to_dict() for k, v in self.skills.items()},
            "superseded_skills": [s.to_dict() for s in self.superseded_skills],
            "attempt_history": list(self.attempt_history),
            "outcome_rings": {k: list(v) for k, v in self.outcome_rings.items()},
            "error_rings": {k: list(v) for k, v in self.error_rings.items()},
            "active_goal_id": self.active_goal_id,
            "play_active": self.play_active,
            "play_purpose": self.play_purpose,
            "authored_order": list(self.authored_order),
            "authored_index": self.authored_index,
            "metrics": dict(self.metrics),
            "seed": self.seed,
            "config": asdict(self.config),
        }

    @classmethod
    def from_state(
        cls, d: dict[str, Any], config: DevelopmentConfig | None = None
    ) -> DevelopmentEngine:
        cfg = config or DevelopmentConfig(**(d.get("config") or {}))
        eng = cls(
            agent_id=str(d["agent_id"]),
            config=cfg,
            seed=d.get("seed"),
        )
        eng.goals = {k: PracticeGoal.from_dict(v) for k, v in (d.get("goals") or {}).items()}
        eng.skills = {k: SkillRecord.from_dict(v) for k, v in (d.get("skills") or {}).items()}
        eng.superseded_skills = [
            SkillRecord.from_dict(s) for s in (d.get("superseded_skills") or [])
        ]
        eng.attempt_history = BoundedRing(
            cfg.max_attempt_history, d.get("attempt_history") or []
        )
        eng.outcome_rings = {
            k: BoundedRing(MAX_OUTCOME_WINDOW, v)
            for k, v in (d.get("outcome_rings") or {}).items()
        }
        eng.error_rings = {
            k: BoundedRing(MAX_OUTCOME_WINDOW, v)
            for k, v in (d.get("error_rings") or {}).items()
        }
        eng.active_goal_id = d.get("active_goal_id")
        eng.play_active = bool(d.get("play_active", False))
        eng.play_purpose = d.get("play_purpose")
        eng.authored_order = list(d.get("authored_order") or [])
        eng.authored_index = int(d.get("authored_index", 0))
        eng.metrics = dict(d.get("metrics") or {})
        eng._bounded_initialized = True
        return eng
