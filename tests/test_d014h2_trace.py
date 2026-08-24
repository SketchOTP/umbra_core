"""D-014H2 production decision-trace contract regressions."""

from __future__ import annotations

import json
from pathlib import Path

from umbra_core.runtime import OrganismConfig, create_organism


def _run(tmp_path: Path, seed: int, trace_path: Path | None, name: str, ticks: int = 8):
    org = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / f"{name}.db"),
            seed=seed,
            decision_trace_path=str(trace_path) if trace_path else None,
        )
    )
    outputs = []
    try:
        for _ in range(ticks):
            result = org.tick_once()
            outputs.append(
                {
                    key: result.get(key)
                    for key in (
                        "tick",
                        "capability",
                        "denied",
                        "H",
                        "outcome",
                        "action_issued",
                        "no_safe_action",
                        "external_displacement",
                    )
                }
            )
    finally:
        org.close()
    rows = []
    if trace_path and trace_path.exists():
        rows = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
    return outputs, rows


def _without_hash(rows):
    return [{key: value for key, value in row.items() if key != "trace_row_hash"} for row in rows]


def test_trace_is_default_disabled(tmp_path):
    outputs, rows = _run(tmp_path, 17, None, "disabled")
    assert len(outputs) == 8
    assert rows == []
    assert not (tmp_path / "disabled.jsonl").exists()


def test_trace_enabled_preserves_observable_output(tmp_path):
    disabled, _ = _run(tmp_path, 271828, None, "disabled")
    enabled, rows = _run(tmp_path, 271828, tmp_path / "enabled.jsonl", "enabled")
    assert enabled == disabled
    assert len(rows) == len(enabled)
    assert len({row["trace_row_hash"] for row in rows}) == len(rows)
    assert all(row["decision_cycle"] is True for row in rows)


def test_trace_replay_is_deterministic(tmp_path):
    _, first = _run(tmp_path, 31415, tmp_path / "first.jsonl", "first")
    _, second = _run(tmp_path, 31415, tmp_path / "second.jsonl", "second")
    assert _without_hash(first) == _without_hash(second)
