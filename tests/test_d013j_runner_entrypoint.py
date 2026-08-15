from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from experiments.d012 import run_formal_p0
from experiments.d012.failure_codes import SupervisionError
from experiments.d012.formal_contract_v2 import CONTRACT_V1, CONTRACT_VERSION, CONTRACT_FINGERPRINT
from experiments.d012.worker_launcher import WorkerClient


class StopAtWorkerLaunch(RuntimeError):
    pass


def _intercept_worker_launch(monkeypatch: pytest.MonkeyPatch) -> dict:
    captured: dict = {}

    def stop(cls, manifest_path: Path, manifest: dict, *, timeout: float = 5.0):
        captured["manifest_path"] = manifest_path
        captured["manifest"] = manifest
        raise StopAtWorkerLaunch()

    monkeypatch.setattr(WorkerClient, "launch", classmethod(stop))
    return captured


def _run_until_worker_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    contract: str = CONTRACT_VERSION,
    formal_trace_paths: dict[str, str] | None = None,
) -> tuple[dict, Path]:
    captured = _intercept_worker_launch(monkeypatch)
    run_root = tmp_path / "campaign"
    evidence_root = tmp_path / "published"
    kwargs = {
        "run_root": run_root,
        "evidence_root": evidence_root,
        "execution_id": "d013j-non-formal-test",
        "starting_commit": run_formal_p0.git("rev-parse", "--short", "HEAD"),
        "directive_id": "UMBRA-D-013J-TEST",
        "verdict_namespace": "D013J_TEST",
        "recovery_contract_version": contract,
        "recovery_contract_fingerprint": CONTRACT_FINGERPRINT if contract == CONTRACT_VERSION else None,
    }
    if formal_trace_paths is not None:
        kwargs["formal_trace_paths"] = formal_trace_paths
    with pytest.raises(StopAtWorkerLaunch):
        run_formal_p0.run(**kwargs)
    return captured, run_root


def _assert_v2_manifest(manifest: dict, run_root: Path) -> None:
    expected = {
        "formal_physiology_trace_path": str(run_root / "evidence" / "PHYSIOLOGY_TRACE.jsonl"),
        "formal_recovery_trace_path": str(run_root / "evidence" / "RECOVERY_TRACE.jsonl"),
        "formal_failure_path": str(run_root / "evidence" / "FIRST_FAILURE.json"),
        "formal_recovery_evaluation_trace_path": str(
            run_root / "evidence" / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
        ),
    }
    for key, value in expected.items():
        assert manifest[key] == value
    assert manifest["formal_recovery_contract_version"] == CONTRACT_VERSION
    assert manifest["contract_fingerprint"] == CONTRACT_FINGERPRINT
    assert manifest["directive"] == "UMBRA-D-013J-TEST"


def _assert_single_evaluator_init(run_root: Path) -> None:
    trace = run_root / "evidence" / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    records = [json.loads(line) for line in trace.read_text().splitlines() if line]
    assert len(records) == 1
    assert records[0]["record_type"] == "EVALUATOR_INIT"
    assert records[0]["contract_version"] == CONTRACT_VERSION
    assert records[0]["contract_fingerprint"] == CONTRACT_FINGERPRINT
    assert "trace_row" not in records[0]


def test_v2_run_without_mapping_uses_canonical_paths_and_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured, run_root = _run_until_worker_launch(tmp_path, monkeypatch)
    _assert_v2_manifest(captured["manifest"], run_root)
    _assert_single_evaluator_init(run_root)


def test_v2_run_honors_complete_explicit_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = {
        "formal_physiology_trace_path": str(tmp_path / "custom" / "physiology.jsonl"),
        "formal_recovery_trace_path": str(tmp_path / "custom" / "recovery.jsonl"),
        "formal_failure_path": str(tmp_path / "custom" / "failure.json"),
        "formal_recovery_evaluation_trace_path": str(tmp_path / "custom" / "evaluation.jsonl"),
    }
    captured, _ = _run_until_worker_launch(
        tmp_path, monkeypatch, formal_trace_paths=custom
    )
    for key, value in custom.items():
        assert captured["manifest"][key] == value
    assert captured["manifest"]["formal_recovery_contract_version"] == CONTRACT_VERSION


def test_v2_run_rejects_partial_explicit_mapping(tmp_path: Path) -> None:
    with pytest.raises(SupervisionError, match="V2 formal trace paths incomplete"):
        run_formal_p0.run(
            run_root=tmp_path / "campaign",
            evidence_root=tmp_path / "published",
            execution_id="d013j-partial-test",
            starting_commit=run_formal_p0.git("rev-parse", "--short", "HEAD"),
            directive_id="UMBRA-D-013J-TEST",
            verdict_namespace="D013J_TEST",
            recovery_contract_version=CONTRACT_VERSION,
            recovery_contract_fingerprint=CONTRACT_FINGERPRINT,
            formal_trace_paths={
                "formal_physiology_trace_path": str(tmp_path / "physiology.jsonl")
            },
        )


def test_v1_without_mapping_preserves_legacy_manifest_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured, _ = _run_until_worker_launch(
        tmp_path, monkeypatch, contract=CONTRACT_V1
    )
    manifest = captured["manifest"]
    assert manifest["formal_recovery_contract_version"] == CONTRACT_V1
    assert manifest["contract_fingerprint"] is None
    for key in (
        "formal_physiology_trace_path",
        "formal_recovery_trace_path",
        "formal_failure_path",
        "formal_recovery_evaluation_trace_path",
    ):
        assert key not in manifest


def test_cli_v2_reaches_worker_boundary_with_complete_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _intercept_worker_launch(monkeypatch)
    run_root = tmp_path / "cli-campaign"
    evidence_root = tmp_path / "cli-published"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_formal_p0.py",
            "--run-root",
            str(run_root),
            "--evidence-root",
            str(evidence_root),
            "--execution-id",
            "d013j-cli-test",
            "--starting-commit",
            run_formal_p0.git("rev-parse", "--short", "HEAD"),
            "--directive-id",
            "UMBRA-D-013J-CLI-TEST",
            "--verdict-namespace",
            "D013J_CLI_TEST",
            "--formal-recovery-contract-version",
            CONTRACT_VERSION,
            "--contract-fingerprint",
            CONTRACT_FINGERPRINT,
        ],
    )
    with pytest.raises(StopAtWorkerLaunch):
        run_formal_p0.main()
    manifest = captured["manifest"]
    expected_root = run_root / "evidence"
    assert manifest["formal_physiology_trace_path"] == str(expected_root / "PHYSIOLOGY_TRACE.jsonl")
    assert manifest["formal_recovery_trace_path"] == str(expected_root / "RECOVERY_TRACE.jsonl")
    assert manifest["formal_failure_path"] == str(expected_root / "FIRST_FAILURE.json")
    assert manifest["formal_recovery_evaluation_trace_path"] == str(
        expected_root / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    )
    assert manifest["formal_recovery_contract_version"] == CONTRACT_VERSION
    assert manifest["contract_fingerprint"] == CONTRACT_FINGERPRINT
    assert manifest["directive"] == "UMBRA-D-013J-CLI-TEST"
    _assert_single_evaluator_init(run_root)