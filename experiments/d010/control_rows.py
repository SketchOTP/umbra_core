"""D-010 experiment row labeling and C0 summary eligibility."""

from __future__ import annotations

from experiments.d010.conditions import (
    CONTROL_CONDITION_IDS,
    QUALIFICATION_BASELINE_CONDITION,
    is_control_condition,
)


def label_experiment_row(row: dict) -> dict:
    """Return a copy of `row` with `control_row=True` when condition is C1–C13."""
    labeled = dict(row)
    condition = str(labeled.get("condition", ""))
    if is_control_condition(condition):
        labeled["control_row"] = True
    return labeled


def rows_eligible_for_c0_summary(rows: list[dict]) -> list[dict]:
    """Filter rows that may contribute to C0 qualification summaries."""
    eligible: list[dict] = []
    for row in rows:
        condition = str(row.get("condition", ""))
        if row.get("control_row"):
            continue
        if condition != QUALIFICATION_BASELINE_CONDITION:
            continue
        if is_control_condition(condition):
            continue
        eligible.append(row)
    return eligible


def assert_row_may_enter_c0_summary(row: dict) -> None:
    if row.get("control_row") or is_control_condition(str(row.get("condition", ""))):
        raise ValueError("control_row_cannot_enter_c0_summary")
