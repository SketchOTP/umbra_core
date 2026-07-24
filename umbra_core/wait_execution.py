"""Durable WAIT execution and anti-reentry suppression (D-010 §3.2–3.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umbra_core.temporal.recurrence import EvidenceLane
from umbra_core.util import canon_json, clamp, new_id, sha256_hex

# ponytail: frozen at D-010 Task 6; hardened at Stage B freeze.
MAXIMUM_WAIT_TICKS = 10
SUPPRESSION_DURATION_TICKS = 8
EXPECTATION_VERSION_BYPASS_EPSILON = 1
MAX_WAIT_EXECUTIONS = 128
MAX_WAIT_SUPPRESSIONS = 128
# ponytail: frozen at D-010 Task 6 hardening; aligned with UNCERTAIN_POSITIVE_CAP.
MAX_FALLBACK_BOUNDED_DELTA = 0.12

TERMINAL_WAIT_STATUSES = frozenset(
    {
        "OCCURRENCE_OBSERVED",
        "INTERRUPTED",
        "EXPIRED",
        "INVALIDATED",
        "FAILED",
    }
)
NON_TERMINAL_WAIT_STATUSES = frozenset({"ADMITTED", "ACTIVE"})


class WaitExecutionError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class FallbackBias:
    candidate_class: str
    bounded_delta: float
    expires_after_ticks: int


def normalize_fallback_bias(bias: FallbackBias | None) -> FallbackBias | None:
    if bias is None:
        return None
    clamped = clamp(
        bias.bounded_delta,
        -MAX_FALLBACK_BOUNDED_DELTA,
        MAX_FALLBACK_BOUNDED_DELTA,
    )
    if clamped == bias.bounded_delta:
        return bias
    return FallbackBias(
        candidate_class=bias.candidate_class,
        bounded_delta=clamped,
        expires_after_ticks=bias.expires_after_ticks,
    )


@dataclass(frozen=True)
class WaitExecution:
    execution_id: str
    recurrence_id: str
    expectation_version: int
    window_start: float
    window_end: float
    started_age_tick: int
    deadline_age_tick: int
    interrupt_conditions_hash: str
    internal_context_key: str
    expected_occurrence_id: str
    status: str
    terminal_reason: str | None = None
    fallback_bias: FallbackBias | None = None

    def is_terminal(self) -> bool:
        return self.status in TERMINAL_WAIT_STATUSES


@dataclass(frozen=True)
class WaitSuppression:
    anti_reentry_key: str
    terminal_reason: str
    suppressed_until_age_tick: int
    source_execution_id: str | None = None
    governance_decision_id: str | None = None
    expectation_version: int = 0


def wait_deadline_age_tick(
    *,
    started_age_tick: int,
    window_end: float,
    maximum_wait_ticks: int = MAXIMUM_WAIT_TICKS,
) -> int:
    return min(started_age_tick + maximum_wait_ticks, int(window_end))


def anti_reentry_key(recurrence_id: str, expectation_version: int) -> str:
    return f"{recurrence_id}:v{expectation_version}"


def compute_interrupt_conditions_hash(conditions: tuple[str, ...]) -> str:
    return sha256_hex(canon_json({"interrupt_conditions": list(conditions)}))


@dataclass
class WaitJournal:
    executions: dict[str, WaitExecution] = field(default_factory=dict)
    suppressions: list[WaitSuppression] = field(default_factory=list)
    _prepared: dict[str, WaitExecution] = field(default_factory=dict)

    def prepare_wait(
        self,
        *,
        recurrence_id: str,
        expectation_version: int,
        window_start: float,
        window_end: float,
        started_age_tick: int,
        maximum_wait_ticks: int = MAXIMUM_WAIT_TICKS,
        interrupt_conditions: tuple[str, ...] = (),
        fallback_bias: FallbackBias | None = None,
        internal_context_key: str = "",
        expected_occurrence_id: str = "",
        execution_id: str | None = None,
    ) -> WaitExecution:
        exec_id = execution_id or new_id()
        existing = self.executions.get(exec_id)
        if existing is not None:
            return existing
        deadline = wait_deadline_age_tick(
            started_age_tick=started_age_tick,
            window_end=window_end,
            maximum_wait_ticks=maximum_wait_ticks,
        )
        prepared = WaitExecution(
            execution_id=exec_id,
            recurrence_id=recurrence_id,
            expectation_version=expectation_version,
            window_start=window_start,
            window_end=window_end,
            started_age_tick=started_age_tick,
            deadline_age_tick=deadline,
            interrupt_conditions_hash=compute_interrupt_conditions_hash(interrupt_conditions),
            internal_context_key=internal_context_key,
            expected_occurrence_id=expected_occurrence_id,
            status="ADMITTED",
            fallback_bias=normalize_fallback_bias(fallback_bias),
        )
        self._prepared[exec_id] = prepared
        return prepared

    def abandon_prepare(self, execution_id: str) -> None:
        self._prepared.pop(execution_id, None)

    def admit_prepared(self, execution_id: str) -> WaitExecution:
        prepared = self._prepared.pop(execution_id, None)
        if prepared is None:
            existing = self.executions.get(execution_id)
            if existing is not None:
                return existing
            raise WaitExecutionError("wait_not_prepared")
        if len(self.executions) >= MAX_WAIT_EXECUTIONS:
            raise WaitExecutionError("wait_execution_cap_exceeded")
        active = WaitExecution(
            execution_id=prepared.execution_id,
            recurrence_id=prepared.recurrence_id,
            expectation_version=prepared.expectation_version,
            window_start=prepared.window_start,
            window_end=prepared.window_end,
            started_age_tick=prepared.started_age_tick,
            deadline_age_tick=prepared.deadline_age_tick,
            interrupt_conditions_hash=prepared.interrupt_conditions_hash,
            internal_context_key=prepared.internal_context_key,
            expected_occurrence_id=prepared.expected_occurrence_id,
            status="ACTIVE",
            fallback_bias=prepared.fallback_bias,
        )
        self.executions[execution_id] = active
        return active

    def finalize(
        self,
        execution_id: str,
        status: str,
        *,
        terminal_reason: str | None = None,
    ) -> WaitExecution:
        if status not in TERMINAL_WAIT_STATUSES:
            raise WaitExecutionError("invalid_terminal_status")
        current = self.executions.get(execution_id)
        if current is None:
            raise WaitExecutionError("wait_execution_missing")
        if current.is_terminal():
            return current
        finalized = WaitExecution(
            execution_id=current.execution_id,
            recurrence_id=current.recurrence_id,
            expectation_version=current.expectation_version,
            window_start=current.window_start,
            window_end=current.window_end,
            started_age_tick=current.started_age_tick,
            deadline_age_tick=current.deadline_age_tick,
            interrupt_conditions_hash=current.interrupt_conditions_hash,
            internal_context_key=current.internal_context_key,
            expected_occurrence_id=current.expected_occurrence_id,
            status=status,
            terminal_reason=terminal_reason or status,
            fallback_bias=current.fallback_bias,
        )
        self.executions[execution_id] = finalized
        self.record_suppression(
            recurrence_id=finalized.recurrence_id,
            expectation_version=finalized.expectation_version,
            terminal_reason=finalized.terminal_reason or status,
            suppressed_until_age_tick=finalized.deadline_age_tick + SUPPRESSION_DURATION_TICKS,
            source_execution_id=execution_id,
        )
        return finalized

    def get_execution(self, execution_id: str) -> WaitExecution | None:
        return self.executions.get(execution_id)

    def active_execution(self) -> WaitExecution | None:
        for execution in self.executions.values():
            if execution.status == "ACTIVE":
                return execution
        return None

    def record_suppression(
        self,
        *,
        recurrence_id: str,
        expectation_version: int,
        terminal_reason: str,
        suppressed_until_age_tick: int,
        source_execution_id: str | None = None,
        governance_decision_id: str | None = None,
    ) -> WaitSuppression:
        if len(self.suppressions) >= MAX_WAIT_SUPPRESSIONS:
            self.suppressions = self.suppressions[-(MAX_WAIT_SUPPRESSIONS - 1) :]
        suppression = WaitSuppression(
            anti_reentry_key=anti_reentry_key(recurrence_id, expectation_version),
            terminal_reason=terminal_reason,
            suppressed_until_age_tick=suppressed_until_age_tick,
            source_execution_id=source_execution_id,
            governance_decision_id=governance_decision_id,
            expectation_version=expectation_version,
        )
        self.suppressions.append(suppression)
        return suppression

    def is_suppressed(
        self,
        recurrence_id: str,
        expectation_version: int,
        effective_age_ticks: int,
    ) -> bool:
        key = anti_reentry_key(recurrence_id, expectation_version)
        for suppression in reversed(self.suppressions):
            if suppression.anti_reentry_key != key:
                continue
            if effective_age_ticks < suppression.suppressed_until_age_tick:
                return True
        return False

    def may_bypass_suppression(
        self,
        recurrence_id: str,
        prior_expectation_version: int,
        new_expectation_version: int,
    ) -> bool:
        _ = recurrence_id
        delta = new_expectation_version - prior_expectation_version
        return delta >= EXPECTATION_VERSION_BYPASS_EPSILON

    def try_complete_with_occurrence(
        self,
        execution_id: str,
        *,
        recurrence_id: str,
        expectation_version: int,
        occurrence_id: str,
        internal_context_key: str,
        observation_age_tick: int,
        lane: EvidenceLane,
    ) -> WaitExecution | None:
        execution = self.executions.get(execution_id)
        if execution is None or execution.is_terminal():
            return execution
        if lane != EvidenceLane.ORGANISM_OBSERVABLE:
            return execution
        if execution.recurrence_id != recurrence_id:
            return execution
        if execution.expectation_version != expectation_version:
            return execution
        if not (execution.window_start <= observation_age_tick <= execution.window_end):
            return execution
        if execution.internal_context_key != internal_context_key:
            return execution
        if execution.expected_occurrence_id != occurrence_id:
            return execution
        return self.finalize(
            execution_id,
            "OCCURRENCE_OBSERVED",
            terminal_reason="o_lane_occurrence_matched",
        )

    def to_state(self) -> dict[str, Any]:
        return {
            "executions": {
                eid: {
                    "execution_id": ex.execution_id,
                    "recurrence_id": ex.recurrence_id,
                    "expectation_version": ex.expectation_version,
                    "window_start": ex.window_start,
                    "window_end": ex.window_end,
                    "started_age_tick": ex.started_age_tick,
                    "deadline_age_tick": ex.deadline_age_tick,
                    "interrupt_conditions_hash": ex.interrupt_conditions_hash,
                    "internal_context_key": ex.internal_context_key,
                    "expected_occurrence_id": ex.expected_occurrence_id,
                    "status": ex.status,
                    "terminal_reason": ex.terminal_reason,
                    "fallback_bias": (
                        {
                            "candidate_class": ex.fallback_bias.candidate_class,
                            "bounded_delta": ex.fallback_bias.bounded_delta,
                            "expires_after_ticks": ex.fallback_bias.expires_after_ticks,
                        }
                        if ex.fallback_bias is not None
                        else None
                    ),
                }
                for eid, ex in sorted(self.executions.items())
            },
            "suppressions": [
                {
                    "anti_reentry_key": s.anti_reentry_key,
                    "terminal_reason": s.terminal_reason,
                    "suppressed_until_age_tick": s.suppressed_until_age_tick,
                    "source_execution_id": s.source_execution_id,
                    "governance_decision_id": s.governance_decision_id,
                    "expectation_version": s.expectation_version,
                }
                for s in self.suppressions
            ],
        }

    @classmethod
    def from_state(cls, data: dict[str, Any]) -> WaitJournal:
        journal = cls()
        for eid, payload in (data.get("executions") or {}).items():
            fb = payload.get("fallback_bias")
            fallback = (
                FallbackBias(
                    candidate_class=str(fb["candidate_class"]),
                    bounded_delta=float(fb["bounded_delta"]),
                    expires_after_ticks=int(fb["expires_after_ticks"]),
                )
                if fb is not None
                else None
            )
            journal.executions[eid] = WaitExecution(
                execution_id=str(payload["execution_id"]),
                recurrence_id=str(payload["recurrence_id"]),
                expectation_version=int(payload["expectation_version"]),
                window_start=float(payload["window_start"]),
                window_end=float(payload["window_end"]),
                started_age_tick=int(payload["started_age_tick"]),
                deadline_age_tick=int(payload["deadline_age_tick"]),
                interrupt_conditions_hash=str(payload["interrupt_conditions_hash"]),
                internal_context_key=str(payload.get("internal_context_key", "")),
                expected_occurrence_id=str(payload.get("expected_occurrence_id", "")),
                status=str(payload["status"]),
                terminal_reason=payload.get("terminal_reason"),
                fallback_bias=normalize_fallback_bias(fallback),
            )
        for payload in data.get("suppressions") or []:
            journal.suppressions.append(
                WaitSuppression(
                    anti_reentry_key=str(payload["anti_reentry_key"]),
                    terminal_reason=str(payload["terminal_reason"]),
                    suppressed_until_age_tick=int(payload["suppressed_until_age_tick"]),
                    source_execution_id=payload.get("source_execution_id"),
                    governance_decision_id=payload.get("governance_decision_id"),
                    expectation_version=int(payload.get("expectation_version", 0)),
                )
            )
        return journal


def apply_wait_recovery_delta(journal: WaitJournal, delta: Any) -> WaitJournal:
    """Apply a recorded WaitRecoveryDelta without re-reading wall clock."""
    execution = journal.executions.get(delta.execution_id)
    if execution is None:
        raise WaitExecutionError("wait_execution_missing")
    if execution.status != delta.expected_status:
        raise WaitExecutionError("wait_status_mismatch")
    if execution.is_terminal():
        return journal
    updated = journal.finalize(
        delta.execution_id,
        delta.terminal_status,
        terminal_reason=delta.terminal_reason,
    )
    _ = updated
    return journal


def apply_wait_recovery_deltas(journal: WaitJournal, deltas: tuple[Any, ...]) -> WaitJournal:
    current = journal
    for delta in deltas:
        current = apply_wait_recovery_delta(current, delta)
    return current


def apply_wait_recovery_delta(journal: WaitJournal, delta: Any) -> WaitJournal:
    """Apply a recorded WaitRecoveryDelta without re-reading wall clock."""
    execution = journal.executions.get(delta.execution_id)
    if execution is None:
        raise WaitExecutionError("wait_execution_missing")
    if execution.status != delta.expected_status:
        raise WaitExecutionError("wait_status_mismatch")
    if execution.is_terminal():
        return journal
    updated = journal.finalize(
        delta.execution_id,
        delta.terminal_status,
        terminal_reason=delta.terminal_reason,
    )
    _ = updated
    return journal


def apply_wait_recovery_deltas(journal: WaitJournal, deltas: tuple[Any, ...]) -> WaitJournal:
    current = journal
    for delta in deltas:
        current = apply_wait_recovery_delta(current, delta)
    return current
