"""Pure interruption-safe accounting for the AS-018 formal runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


STAGES = (
    "REGISTERED",
    "STARTED",
    "EXECUTION_FINISHED",
    "VALIDATION_STARTED",
    "LOCALLY_VALIDATED",
    "EXPORT_VERIFIED",
    "CASE_FINISHED",
)


class AccountingError(RuntimeError):
    """Raised when a formal case attempts an invalid accounting transition."""


@dataclass
class FormalAccounting:
    """Track case lifecycle without creating organisms or retrying work."""

    case_ids: tuple[str, ...]
    states: dict[str, str] = field(default_factory=dict)
    consumed: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if len(self.case_ids) != 32 or len(set(self.case_ids)) != 32:
            raise AccountingError("AS018_FORMAL_CASE_REGISTRATION_INVALID")
        self.states = {case_id: "REGISTERED" for case_id in self.case_ids}

    def _require(self, case_id: str, expected: str) -> None:
        if case_id not in self.states or self.states[case_id] != expected:
            raise AccountingError(
                f"AS018_FORMAL_STAGE_INVALID:{case_id}:{self.states.get(case_id)}:{expected}"
            )

    def start(self, case_id: str) -> None:
        self._require(case_id, "REGISTERED")
        self.states[case_id] = "STARTED"
        self.consumed.add(case_id)

    def execution_finished(self, case_id: str) -> None:
        self._require(case_id, "STARTED")
        self.states[case_id] = "EXECUTION_FINISHED"

    def validation_started(self, case_id: str) -> None:
        self._require(case_id, "EXECUTION_FINISHED")
        self.states[case_id] = "VALIDATION_STARTED"

    def locally_validated(self, case_id: str) -> None:
        self._require(case_id, "VALIDATION_STARTED")
        self.states[case_id] = "LOCALLY_VALIDATED"

    def export_verified(self, case_id: str) -> None:
        self._require(case_id, "LOCALLY_VALIDATED")
        self.states[case_id] = "EXPORT_VERIFIED"

    def finish(self, case_id: str) -> None:
        self._require(case_id, "EXPORT_VERIFIED")
        self.states[case_id] = "CASE_FINISHED"

    def reject(self, case_id: str) -> None:
        if self.states.get(case_id) not in {"EXECUTION_FINISHED", "VALIDATION_STARTED"}:
            raise AccountingError(f"AS018_FORMAL_REJECTION_STAGE_INVALID:{case_id}")
        self.states[case_id] = "CASE_REJECTED"

    def interrupt(self, case_id: str) -> None:
        if case_id not in self.states:
            raise AccountingError(f"AS018_FORMAL_UNKNOWN_CASE:{case_id}")
        if self.states[case_id] == "CASE_FINISHED":
            raise AccountingError(f"AS018_FORMAL_FINISHED_CASE_INTERRUPTED:{case_id}")
        self.states[case_id] = "INTERRUPTED"

    def summary(self) -> dict[str, object]:
        accepted = sum(state == "CASE_FINISHED" for state in self.states.values())
        started = sum(case_id in self.consumed for case_id in self.states)
        unresolved = sorted(
            case_id for case_id, state in self.states.items() if state != "CASE_FINISHED"
        )
        return {
            "registered_cases": len(self.states),
            "started_cases": started,
            "accepted_cases": accepted,
            "formal_seed_consumption": len(self.consumed),
            "case_states": dict(sorted(self.states.items())),
            "unresolved_cases": unresolved,
            "population_acceptance_ready": (
                len(self.states) == 32
                and started == 32
                and accepted == 32
                and not unresolved
            ),
        }


__all__ = ["AccountingError", "FormalAccounting", "STAGES"]
