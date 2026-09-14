from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.as017 import qualification
from tools.as017_evidence import StageJournal, summarize_stage_journal
from tools.as017_formal_acceptance import accept_case


def _manifest() -> dict:
    return json.loads(
        Path("experiments/as017/AS017_FORMAL_SEED_MANIFEST_V1.json").read_text()
    )


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


def test_formal_execute_requires_case_acceptance_callback(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="ACCEPTANCE_CALLBACK_REQUIRED"):
        qualification.execute(
            _manifest(),
            tmp_path / "work",
            candidate_commit="candidate",
            manifest_sha256="manifest",
        )
    assert not (tmp_path / "work").exists()


def test_formal_execute_reports_actual_started_seed_count(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(regime: str, seed: int, work: Path, horizon: int) -> dict:
        return _row(regime, seed, 0)

    monkeypatch.setattr(qualification, "run_development_case", fake_run)
    starts: list[dict] = []
    result = qualification.execute(
        _manifest(),
        tmp_path / "work",
        candidate_commit="candidate",
        manifest_sha256="manifest",
        on_case_start=starts.append,
        accept_case=lambda row: {"verdict": "PASS", "case_id": f"{row['regime']}-{row['seed']}"},
    )
    assert result["terminal"] == "AS017_FORMAL_POPULATION_PASS"
    assert result["completed_runs"] == 32
    assert result["accepted_cases"] == 32
    assert result["formal_seed_consumption"] == 32
    assert len(starts) == 32


def test_formal_execute_rejects_case_without_false_population_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(regime: str, seed: int, work: Path, horizon: int) -> dict:
        return _row(regime, seed, 0)

    monkeypatch.setattr(qualification, "run_development_case", fake_run)
    result = qualification.execute(
        _manifest(),
        tmp_path / "work",
        candidate_commit="candidate",
        manifest_sha256="manifest",
        accept_case=lambda row: {"verdict": "FAIL", "failures": ["synthetic_validation_failure"]},
    )
    assert result["all_completed"] is False
    assert result["terminal"] == "AS017_FORMAL_R0_CASE_ACCEPTANCE_FAIL"
    assert result["completed_runs"] == 0
    assert result["accepted_cases"] == 0
    assert result["formal_seed_consumption"] == 1
    assert len(result["started_cases"]) == 1


def test_formal_acceptance_rejects_completed_row_without_required_artifacts(tmp_path: Path) -> None:
    journal_path = tmp_path / "stages.jsonl"
    journal = StageJournal(journal_path)
    row = _row("R0", 43096946, 0)
    row.update(candidate_commit="candidate", seed_manifest_sha256="manifest")
    report = accept_case(row, tmp_path / "work", "candidate", "manifest", journal)
    journal.close()
    assert report["verdict"] == "FAIL"
    assert "required_local_artifact_missing" in report["failures"]
    assert summarize_stage_journal(journal_path)["acceptance_ready"] is False
