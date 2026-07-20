"""Bounded causal forward/inverse model store (independent of Replicode)."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any


# Preregistered resource caps (Gate 8).
MAX_MODELS = 200
MAX_PLAN_DEPTH = 4
MAX_COMPOSITION_NODES = 64


@dataclass
class CausalModel:
    model_id: str
    context_features: tuple[str, ...]  # structural features (generalizable)
    action: str
    outcome: str
    support: int = 0
    contradict: int = 0
    invalidated: bool = False
    superseded_by: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def confidence(self) -> float:
        n = self.support + self.contradict
        if n == 0:
            return 0.0
        return self.support / n

    @property
    def active(self) -> bool:
        return not self.invalidated and self.superseded_by is None

    def key(self) -> tuple[tuple[str, ...], str, str]:
        return (self.context_features, self.action, self.outcome)


class ModelStore:
    """Learns context+action → outcome with confidence and supersession."""

    def __init__(self, max_models: int = MAX_MODELS, handle_contradiction: bool = True):
        self.max_models = max_models
        self.handle_contradiction = handle_contradiction
        self._models: dict[str, CausalModel] = {}
        self._seq = 0
        self.cpu_ops = 0

    def _new_id(self) -> str:
        self._seq += 1
        return f"m{self._seq}"

    def active_models(self) -> list[CausalModel]:
        return [m for m in self._models.values() if m.active]

    def model_count(self) -> int:
        return len(self.active_models())

    def observe(
        self,
        context_features: tuple[str, ...],
        action: str,
        outcome: str,
        *,
        allow_create: bool = True,
    ) -> CausalModel | None:
        """Update supporting/contradicting evidence; maybe create or supersede."""
        self.cpu_ops += 1
        ctx = tuple(sorted(context_features))
        # Exact match on (ctx, action, outcome)
        exact = next(
            (
                m
                for m in self.active_models()
                if m.context_features == ctx and m.action == action and m.outcome == outcome
            ),
            None,
        )
        # Same context+action, different outcome → contradiction / rival
        rivals = [
            m
            for m in self.active_models()
            if m.context_features == ctx and m.action == action and m.outcome != outcome
        ]

        if exact:
            exact.support += 1
            exact.updated_at = time.time()
            if self.handle_contradiction:
                for r in rivals:
                    r.contradict += 1
                    r.updated_at = time.time()
                    self._maybe_invalidate(r, winner=exact)
            return exact

        if not allow_create:
            for r in rivals:
                r.contradict += 1
            return None

        if self.model_count() >= self.max_models:
            self._evict_weakest()

        mid = self._new_id()
        m = CausalModel(
            model_id=mid,
            context_features=ctx,
            action=action,
            outcome=outcome,
            support=1,
        )
        self._models[mid] = m
        if self.handle_contradiction:
            for r in rivals:
                r.contradict += 1
                r.updated_at = time.time()
                self._maybe_invalidate(r, winner=m)
        return m

    def _maybe_invalidate(self, loser: CausalModel, winner: CausalModel) -> None:
        if not self.handle_contradiction or not loser.active:
            return
        # Obsolete when contradict dominates and winner is stronger
        if loser.contradict > loser.support and winner.confidence >= loser.confidence:
            loser.invalidated = True
            loser.superseded_by = winner.model_id
            loser.updated_at = time.time()

    def _evict_weakest(self) -> None:
        active = self.active_models()
        if not active:
            return
        weakest = min(active, key=lambda m: (m.confidence, m.support, m.updated_at))
        weakest.invalidated = True
        weakest.updated_at = time.time()

    def predict(self, context_features: tuple[str, ...], action: str) -> tuple[str | None, float]:
        """Best predicted outcome for context+action among active models."""
        self.cpu_ops += 1
        ctx = tuple(sorted(context_features))
        cands = [
            m
            for m in self.active_models()
            if m.action == action and self._feature_match(m.context_features, ctx)
        ]
        if not cands:
            return None, 0.0
        best = max(cands, key=lambda m: (m.confidence, m.support, -len(m.context_features)))
        return best.outcome, best.confidence

    def _feature_match(self, model_ctx: tuple[str, ...], obs_ctx: tuple[str, ...]) -> bool:
        # Structural generalization: model features ⊆ observation features
        return set(model_ctx).issubset(set(obs_ctx))

    def inverse(
        self,
        desired_outcome: str,
        context_features: tuple[str, ...] | None = None,
        *,
        randomized: bool = False,
        rng: Any = None,
    ) -> list[CausalModel]:
        """desired outcome → candidate models (action/context), ranked by confidence."""
        self.cpu_ops += 1
        cands = [m for m in self.active_models() if m.outcome == desired_outcome]
        if context_features is not None:
            ctx = set(context_features)
            # Prefer models whose context is compatible with current features
            cands = [m for m in cands if set(m.context_features).issubset(ctx) or not m.context_features]
        cands.sort(key=lambda m: (m.confidence, m.support), reverse=True)
        if randomized and rng is not None and cands:
            rng.shuffle(cands)
        return cands

    def seed_model(
        self,
        context_features: tuple[str, ...],
        action: str,
        outcome: str,
        support: int = 10,
    ) -> CausalModel:
        """Designer-supplied model (C0). Marked as high support, not learned from stream."""
        m = self.observe(context_features, action, outcome)
        assert m is not None
        m.support = support
        return m

    def dump(self) -> list[dict]:
        return [
            {
                "model_id": m.model_id,
                "context_features": list(m.context_features),
                "action": m.action,
                "outcome": m.outcome,
                "support": m.support,
                "contradict": m.contradict,
                "confidence": m.confidence,
                "invalidated": m.invalidated,
                "superseded_by": m.superseded_by,
            }
            for m in self._models.values()
        ]

    def save_sqlite(self, path: str) -> None:
        conn = sqlite3.connect(path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS models (
            model_id TEXT PRIMARY KEY,
            context_features TEXT,
            action TEXT,
            outcome TEXT,
            support INT,
            contradict INT,
            invalidated INT,
            superseded_by TEXT
        )"""
        )
        conn.execute("DELETE FROM models")
        for m in self._models.values():
            conn.execute(
                "INSERT INTO models VALUES (?,?,?,?,?,?,?,?)",
                (
                    m.model_id,
                    json.dumps(list(m.context_features)),
                    m.action,
                    m.outcome,
                    m.support,
                    m.contradict,
                    int(m.invalidated),
                    m.superseded_by,
                ),
            )
        conn.commit()
        conn.close()

    @classmethod
    def load_sqlite(cls, path: str, **kwargs: Any) -> ModelStore:
        store = cls(**kwargs)
        conn = sqlite3.connect(path)
        rows = conn.execute("SELECT * FROM models").fetchall()
        conn.close()
        for mid, ctx, action, outcome, support, contradict, inv, sup in rows:
            m = CausalModel(
                model_id=mid,
                context_features=tuple(json.loads(ctx)),
                action=action,
                outcome=outcome,
                support=support,
                contradict=contradict,
                invalidated=bool(inv),
                superseded_by=sup,
            )
            store._models[mid] = m
            n = int(mid[1:]) if mid.startswith("m") and mid[1:].isdigit() else 0
            store._seq = max(store._seq, n)
        return store
