"""Synthetic live frozen-CLI wiring, not an organism or scientific campaign."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import pytest

from experiments.as018 import qualification
from tools import as017_formal_acceptance, as018_run_formal
from tools.as017_evidence import iter_jsonl
from tools.umbra_baseline_audit import validate_accounting
from umbra_core.decision_trace import DecisionTraceSink


@pytest.fixture(scope="module")
def original_journal(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("frozen-cli-synthetic")
    monkeypatch = pytest.MonkeyPatch()
    # All 32 are synthetic protocol identities, never frozen/formal seeds.
    manifest = {
        "schema": "AS018_FORMAL_SEED_MANIFEST_V2", "directive": "UMBRA-AS-018",
        "seed_status": "frozen_before_formal_execution",
        "organism_implementation_sha": qualification.ORGANISM_IMPLEMENTATION_SHA,
        "formal_execution_subject": "a" * 40,
        "formal_regimes": {regime: list(range(700001 + i * 8, 700009 + i * 8))
                           for i, regime in enumerate(("R0", "R1", "R2", "R3"))},
        "ticks_per_organism": 7200, "total_organisms": 32, "total_ticks": 230400,
        "retries": 0, "reseeds": 0, "substitutions": 0, "formal_seeds_consumed": 0,
    }
    manifest_path = tmp_path / "synthetic-manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    source = tmp_path / "synthetic-trace.jsonl"
    sink = DecisionTraceSink(str(source), mode="compact_acceptance")
    for tick in range(1, 7201):
        assert sink.record({"tick": tick, "active_ticks": tick,
                            "physiology": {"energy": .8, "fatigue": .2, "integrity": 1., "stimulation": .4},
                            "final_candidate": {"capability": "IDLE", "params": {}}})
    sink.close()
    calls = []

    def fake_run(regime, seed, work, horizon):
        calls.append((regime, seed))
        (work / f"{regime}-{seed}.sqlite").write_bytes(b"synthetic journal-wiring database, not an organism")
        name = f"{regime}-{seed}.jsonl"
        shutil.copyfile(source, work / name)
        return {"seed": seed, "terminal": "completed", "ticks": horizon, "target_ticks": horizon,
                "critical_failure": None, "first_no_safe_action": None,
                "configuration": {"seed": seed}, "recovery_reachability_enabled": True,
                "decision_trace_filename": name}

    def never_create(*args, **kwargs):
        pytest.fail("journal qualification must not create an organism")

    import umbra_core.runtime
    monkeypatch.setattr(umbra_core.runtime, "create_organism", never_create)
    monkeypatch.setattr(qualification, "run_case", fake_run)
    # Database content is deliberately stubbed: this test qualifies the real
    # callback/export journal format, not SQLite or organism viability.
    monkeypatch.setattr(as017_formal_acceptance, "_validate_database", lambda *a, **k:
                        {"verdict": "PASS", "failures": [], "identity_present": True})
    monkeypatch.setattr(as018_run_formal, "require_clean_candidate", lambda value: value)
    monkeypatch.setattr(as018_run_formal, "require_lock", lambda *a:
                        {"seed_contract": {"manifest_sha256": as018_run_formal.stream_sha256(manifest_path)},
                         "formal_execution_subject": "a" * 40})
    work, result = tmp_path / "work", tmp_path / "result.json"
    monkeypatch.setattr(sys, "argv", ["as018_run_formal.py", "--manifest", str(manifest_path),
                                     "--lock", str(tmp_path / "synthetic-lock.json"), "--lock-sha256", "synthetic",
                                     "--work", str(work), "--result", str(result), "--candidate-commit", "synthetic"])
    try:
        as018_run_formal.main()
    finally:
        monkeypatch.undo()
    expected = {f"{r}-{i:02d}-{s}": (r, i, s) for r in manifest["formal_regimes"]
                for i, s in enumerate(manifest["formal_regimes"][r])}
    path = tmp_path / "work.stages.jsonl"
    assert len(calls) == 32
    return path, expected, list(iter_jsonl(path))


def test_exact_frozen_cli_journal_is_accepted(original_journal):
    path, expected, rows = original_journal
    assert sum(r["stage"] == "REGISTERED_CASE" for r in rows) == 32
    assert sum(r["stage"] == "VALIDATION_STARTED" for r in rows) == 64
    report = validate_accounting(path, expected)
    assert report["verdict"] == "PASS", report
    assert report["summary"]["stage_counts"]["VALIDATION_STARTED"] == 64


@pytest.mark.parametrize("mutation", ["duplicate_start", "third_validation", "missing_registration",
                                     "wrong_validation_order", "missing_export", "wrong_seed"])
def test_real_journal_mutations_remain_rejected(original_journal, tmp_path, mutation):
    _, expected, rows = original_journal
    rows = json.loads(json.dumps(rows))
    first = next(i for i, row in enumerate(rows) if row["stage"] == "STARTED")
    validation = next(i for i, row in enumerate(rows) if row["stage"] == "VALIDATION_STARTED")
    if mutation == "duplicate_start":
        rows.insert(first + 1, dict(rows[first]))
    elif mutation == "third_validation":
        rows.insert(validation + 2, dict(rows[validation + 1]))
    elif mutation == "missing_registration":
        rows.pop(next(i for i, row in enumerate(rows) if row["stage"] == "REGISTERED_CASE"))
    elif mutation == "wrong_validation_order":
        rows[validation], rows[validation + 1] = rows[validation + 1], rows[validation]
    elif mutation == "missing_export":
        rows.pop(next(i for i, row in enumerate(rows) if row["stage"] == "EXPORT_VERIFIED"))
    elif mutation == "wrong_seed":
        rows[first]["seed"] += 1
    path = tmp_path / "altered.stages.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert validate_accounting(path, expected)["verdict"] == "FAIL"
