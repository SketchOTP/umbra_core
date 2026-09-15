from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.as018 import qualification
from tools.as017_evidence import StageJournal, summarize_stage_journal
from tools.as018_run_formal import append_started_record


def _manifest() -> dict:
    return {
        "schema": "AS018_FORMAL_SEED_MANIFEST_V2",
        "directive": "UMBRA-AS-018",
        "seed_status": "frozen_before_formal_execution",
        "organism_implementation_sha": "e8d048b510a477e677637b67bc0f56473cfe6540",
        "formal_execution_subject": "a" * 40,
        "formal_regimes": {
            "R0": list(range(700001, 700009)),
            "R1": list(range(700009, 700017)),
            "R2": list(range(700017, 700025)),
            "R3": list(range(700025, 700033)),
        },
        "ticks_per_organism": 7200,
        "total_organisms": 32,
        "total_ticks": 230400,
        "retries": 0,
        "reseeds": 0,
        "substitutions": 0,
        "formal_seeds_consumed": 0,
    }


def test_live_runner_started_callback_writes_one_reserved_stage_record(tmp_path: Path) -> None:
    path = tmp_path / "stages.jsonl"
    journal = StageJournal(path)
    append_started_record(
        journal,
        {
            "case_id": "R0-00-700001",
            "regime": "R0",
            "seed": 700001,
            "seed_index": 0,
            "target_ticks": 7200,
        },
    )
    journal.close()
    row = json.loads(path.read_text().strip())
    assert row == {
        "schema": "AS017_STAGE_RECORD_V1",
        "stage": "STARTED",
        "case_id": "R0-00-700001",
        "regime": "R0",
        "seed": 700001,
        "seed_index": 0,
        "target_ticks": 7200,
    }


def _row(regime: str, seed: int, seed_index: int) -> dict:
    return {
        "terminal": "completed",
        "ticks": 7200,
        "target_ticks": 7200,
        "critical_failure": None,
        "first_no_safe_action": None,
        "configuration": {"seed": seed},
        "regime": regime,
        "scenario": {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}[regime],
        "seed": seed,
        "seed_index": seed_index,
    }


def test_live_started_callback_is_durable_before_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = _manifest()
    journal = StageJournal(tmp_path / "stages.jsonl")
    events: list[str] = []
    executed = 0

    def on_start(info: dict[str, object]) -> None:
        events.append("durable_started")
        journal.append(
            "STARTED",
            case_id=str(info["case_id"]),
            regime=str(info["regime"]),
            seed=int(info["seed"]),
            seed_index=int(info["seed_index"]),
            target_ticks=int(info["target_ticks"]),
        )

    def fake_run(regime: str, seed: int, work: Path, horizon: int) -> dict:
        nonlocal executed
        executed += 1
        events.append("organism_execution")
        return _row(regime, seed, 0)

    monkeypatch.setattr(qualification, "run_case", fake_run)
    result = qualification.execute(
        manifest,
        tmp_path / "work",
        candidate_commit="candidate",
        manifest_sha256="manifest",
        on_case_start=on_start,
        accept_case=lambda row: {"verdict": "PASS"},
    )
    journal.close()
    assert result["formal_seed_consumption"] == 32
    assert executed == 32
    assert events[:2] == ["durable_started", "organism_execution"]
    assert summarize_stage_journal(tmp_path / "stages.jsonl")["journal_status"] == "VALID"


def test_failure_before_started_record_consumes_no_seed_and_executes_no_organism(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = _manifest()
    executed = 0

    def on_start(info: dict[str, object]) -> None:
        raise OSError("synthetic journal write failure")

    def fake_run(regime: str, seed: int, work: Path, horizon: int) -> dict:
        nonlocal executed
        executed += 1
        return _row(regime, seed, 0)

    monkeypatch.setattr(qualification, "run_case", fake_run)
    with pytest.raises(OSError, match="synthetic journal write failure"):
        qualification.execute(
            manifest,
            tmp_path / "work",
            candidate_commit="candidate",
            manifest_sha256="manifest",
            on_case_start=on_start,
            accept_case=lambda row: {"verdict": "PASS"},
        )
    assert executed == 0


def test_failure_after_started_record_consumes_seed_but_not_organism(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = _manifest()
    journal = StageJournal(tmp_path / "stages.jsonl")
    events: list[str] = []

    def on_start(info: dict[str, object]) -> None:
        journal.append(
            "STARTED",
            case_id=str(info["case_id"]),
            regime=str(info["regime"]),
            seed=int(info["seed"]),
            seed_index=int(info["seed_index"]),
            target_ticks=int(info["target_ticks"]),
        )
        events.append("durable_started")

    def fake_run(regime: str, seed: int, work: Path, horizon: int) -> dict:
        events.append("execution_called")
        raise RuntimeError("synthetic failure after durable start")

    monkeypatch.setattr(qualification, "run_case", fake_run)
    with pytest.raises(RuntimeError, match="synthetic failure after durable start"):
        qualification.execute(
            manifest,
            tmp_path / "work",
            candidate_commit="candidate",
            manifest_sha256="manifest",
            on_case_start=on_start,
            accept_case=lambda row: {"verdict": "PASS"},
        )
    journal.close()
    rows = [json.loads(line) for line in (tmp_path / "stages.jsonl").read_text().splitlines()]
    assert rows[0]["stage"] == "STARTED"
    assert events == ["durable_started", "execution_called"]


def test_live_stage_sequence_reconciles_and_rejection_cannot_pass(tmp_path: Path) -> None:
    journal = StageJournal(tmp_path / "stages.jsonl")
    case_id = "SYNTH-00-700001"
    journal.append("REGISTERED", expected_cases=1)
    journal.append("REGISTERED_CASE", case_id=case_id)
    journal.append("STARTED", case_id=case_id)
    journal.append("EXECUTION_FINISHED", case_id=case_id, ticks=7200)
    journal.append("VALIDATION_STARTED", case_id=case_id)
    journal.append("CASE_REJECTED", case_id=case_id, failures=["synthetic_failure"])
    journal.close()
    summary = summarize_stage_journal(tmp_path / "stages.jsonl")
    assert summary["case_states"][case_id] == "CASE_REJECTED"
    assert summary["acceptance_ready"] is False
