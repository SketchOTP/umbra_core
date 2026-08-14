from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.d012.formal_contract_v2 import (
    CONTRACT_FINGERPRINT,
    CONTRACT_VERSION,
    RECOVERY_FAILED,
    RECOVERY_SUCCESS,
    SAFE_DENIAL,
    evaluate_episode,
    normalize_trace_row,
)
from experiments.d012.failure_codes import SupervisionError
from experiments.d012.organism_worker import Worker
from experiments.d012.run_formal_p0 import (
    REQUIRED_OUTPUTS,
    V2_REQUIRED_OUTPUTS,
    evaluator_initialization_record,
    formal_failure_from_metrics,
    publish_evidence,
)
from experiments.d012.worker_launcher import manifest_for

from test_d013f_formal_contract_v2 import _row, _success


def _manifest(
    root: Path,
    *,
    execution_id: str = "umbra-d013h-non-formal-001",
    generation: int = 1,
    trace_path: Path | None = None,
    contract_fingerprint: str = CONTRACT_FINGERPRINT,
    **flags: object,
) -> dict[str, object]:
    return manifest_for(
        root,
        execution_id=execution_id,
        generation=generation,
        ownership_generation=generation,
        freeze_manifest_hash="fixture-freeze",
        active_runtime=0.0,
        formal_recovery_contract_version=CONTRACT_VERSION,
        contract_fingerprint=contract_fingerprint,
        formal_physiology_trace_path=str(root / "PHYSIOLOGY_TRACE.jsonl"),
        formal_recovery_trace_path=str(root / "RECOVERY_TRACE.jsonl"),
        formal_recovery_evaluation_trace_path=str(
            trace_path or root / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
        ),
        formal_failure_path=str(root / "FIRST_FAILURE.json"),
        directive="UMBRA-D-013H-NON-FORMAL",
        starting_commit="cf29ac28b2e51a36f450df490e756344b85e6c78",
        configuration_fingerprint="non-formal-config",
        verdict_namespace="D013H",
        **flags,
    )


def _denial(observation_id: str, observed_at: float, distance: float) -> dict:
    row = _row()
    for key in ("observation_signature", "new_evidence", "corrective_action", "recovery_blocked"):
        row.pop(key, None)
    row["observations"] = [{
        "observation_id": observation_id,
        "observed_at": observed_at,
        "kind": "resource",
        "estimated_distance": distance,
        "confidence": 0.89,
        "uncertainty": 0.11,
    }]
    row["available_recovery_affordances"] = [{
        "kind": "resource",
        "radius": 1.2,
        "chargeable": True,
        "executable": False,
    }]
    return row


def _approach(observation_id: str, observed_at: float, distance: float) -> dict:
    row = _denial(observation_id, observed_at, distance)
    row.update({
        "selected_candidate": "APPROACH",
        "executed_capability": "APPROACH",
        "verified_outcome": {
            "action_issued": True,
            "verified": True,
            "outcome": {
                "capability": "APPROACH",
                "success": True,
                "reason": "ok",
                "effects": {"energy": -0.004},
                "verified": True,
            },
        },
    })
    return row


def test_real_perception_cycles_ignore_ephemeral_ids_and_jitter(tmp_path: Path):
    manifest = _manifest(tmp_path, diagnostic_recovery_reachable=True)
    worker = Worker(manifest)
    worker.acquire_and_load(reclaim_dead=False)
    try:
        rows = worker.run_diagnostic_ticks(2)
        assert rows[0]["observations"] and rows[1]["observations"]
        first = normalize_trace_row(rows[0])
        second = normalize_trace_row(rows[1], first)
        assert rows[0]["observations"][0]["observation_id"] != rows[1]["observations"][0]["observation_id"]
        assert rows[0]["observations"][0]["observed_at"] != rows[1]["observations"][0]["observed_at"]
        assert rows[0]["observations"][0]["estimated_distance"] != rows[1]["observations"][0]["estimated_distance"]
        assert first["material_evidence_key"] == second["material_evidence_key"]
        assert second["material_evidence_changed"] is False
        assert second["new_evidence"] is False
    finally:
        worker.quiesce()


def test_real_perception_path_detects_material_resource_change(tmp_path: Path):
    manifest = _manifest(tmp_path, diagnostic_recovery_reachable=True)
    worker = Worker(manifest)
    worker.acquire_and_load(reclaim_dead=False)
    try:
        first = normalize_trace_row(worker.run_diagnostic_ticks(1)[0])
        resource = next(
            obj for obj in worker.engine.snapshot_view().objects.values()
            if obj.location.__class__.__name__ == "FreeLocation"
        )
        previous = first
        changed = False
        for step in range(1, 20):
            worker.engine.commit_free_location(resource.object_id, 10.0 + step, 0.0)
            current = normalize_trace_row(worker.run_diagnostic_ticks(1)[0], previous)
            if current["material_evidence_changed"]:
                changed = True
                break
            previous = current
        assert changed, (first["material_evidence_key"], previous["material_evidence_key"])
    finally:
        worker.quiesce()


def test_pathological_retry_fails_despite_new_packet_uuid_time_and_jitter(tmp_path: Path):
    worker = Worker(_manifest(tmp_path))
    assert worker._record_v2_recovery_evaluation(_denial("obs-a", 10.0, 1.34)) is None
    result = worker._record_v2_recovery_evaluation(_denial("obs-b", 11.0, 1.29))
    assert result is not None and result.startswith(RECOVERY_FAILED + ":"), [
        (row.get("material_evidence_key"), row.get("material_evidence_changed"), row.get("new_evidence"), row.get("recovery_blocked"))
        for row in worker.recovery_episode_rows
    ] + [evaluate_episode(worker.recovery_episode_rows)]
    trace = [json.loads(line) for line in (tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl").read_text().splitlines()]
    assert trace[-1]["material_evidence_changed"] is False
    assert trace[-1]["new_evidence"] is False
    assert trace[-1]["state"] == RECOVERY_FAILED


def test_corrective_retry_reaches_verified_recovery_success(tmp_path: Path):
    worker = Worker(_manifest(tmp_path))
    assert worker._record_v2_recovery_evaluation(_denial("obs-a", 10.0, 1.34)) is None
    assert worker._record_v2_recovery_evaluation(_approach("obs-b", 11.0, 1.80)) is None
    success = _success(
        observations=[{
            "observation_id": "obs-c",
            "observed_at": 12.0,
            "kind": "resource",
            "estimated_distance": 1.30,
            "confidence": 0.9,
            "uncertainty": 0.1,
        }],
        available_recovery_affordances=[{
            "kind": "resource", "radius": 1.2, "chargeable": True, "executable": True,
        }],
        observation_signature=None,
    )
    for key in ("new_evidence", "corrective_action", "recovery_blocked"):
        success.pop(key, None)
    assert worker._record_v2_recovery_evaluation(success) is None
    assert worker.recovery_episode_rows[-1]["material_evidence_changed"] is True
    trace = [json.loads(line) for line in (tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl").read_text().splitlines()]
    assert trace[-1]["state"] == RECOVERY_SUCCESS


def test_evaluator_context_survives_worker_generation_replacement(tmp_path: Path):
    trace_path = tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    first = Worker(_manifest(tmp_path, generation=1, trace_path=trace_path))
    assert first._record_v2_recovery_evaluation(_denial("obs-a", 10.0, 1.34)) is None
    replacement = Worker(_manifest(tmp_path, generation=2, trace_path=trace_path))
    assert len(replacement.recovery_episode_rows) == 1
    failure = replacement._record_v2_recovery_evaluation(_denial("obs-b", 11.0, 1.29))
    assert failure is not None and failure.startswith(RECOVERY_FAILED + ":"), replacement.recovery_episode_rows


def test_cross_restart_corrective_recovery_survives_generation_replacement(tmp_path: Path):
    trace_path = tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    first = Worker(_manifest(tmp_path, generation=1, trace_path=trace_path))
    assert first._record_v2_recovery_evaluation(_denial("obs-a", 10.0, 1.34)) is None
    replacement = Worker(_manifest(tmp_path, generation=2, trace_path=trace_path))
    assert replacement._record_v2_recovery_evaluation(_approach("obs-b", 11.0, 1.80)) is None
    success = _success(observations=[{
        "observation_id": "obs-c", "observed_at": 12.0, "kind": "resource",
        "estimated_distance": 1.3, "confidence": 0.9, "uncertainty": 0.1,
    }], available_recovery_affordances=[{
        "kind": "resource", "radius": 1.2, "chargeable": True, "executable": True,
    }])
    for key in ("new_evidence", "corrective_action", "recovery_blocked"):
        success.pop(key, None)
    assert replacement._record_v2_recovery_evaluation(success) is None


def test_cross_run_evaluator_context_is_rejected(tmp_path: Path):
    trace_path = tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    first = Worker(_manifest(tmp_path, execution_id="campaign-a", trace_path=trace_path))
    assert first._record_v2_recovery_evaluation(_denial("obs-a", 10.0, 1.34)) is None
    with pytest.raises(SupervisionError, match="evaluator_trace_identity:formal_execution_id"):
        Worker(_manifest(tmp_path, execution_id="campaign-b", trace_path=trace_path))


def test_v2_legacy_terminal_code_fails_closed_and_v1_is_unchanged():
    metrics = {"formal_failure": {"failure": "charge_selected_but_not_executable"}}
    assert formal_failure_from_metrics(metrics, CONTRACT_VERSION) == "V2_CONTRACT_PATH_INCONSISTENCY"
    assert formal_failure_from_metrics(metrics, "P0_RECOVERY_CONTRACT_V1") == "charge_selected_but_not_executable"


def _write_base_outputs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_OUTPUTS:
        (path / name).write_text("NON_FORMAL_TEST\n")


def test_v2_publication_requires_both_final_artifacts(tmp_path: Path):
    work = tmp_path / "work"
    final = tmp_path / "final"
    _write_base_outputs(work)
    for name in V2_REQUIRED_OUTPUTS:
        (work / name).write_text("NON_FORMAL_TEST\n")
    publish_evidence(work, final, CONTRACT_VERSION)
    assert all((final / name).exists() for name in V2_REQUIRED_OUTPUTS)

    missing_trace = tmp_path / "missing-trace"
    _write_base_outputs(missing_trace)
    (missing_trace / "P0_READONLY_POSTRUN_VALIDATION.json").write_text("NON_FORMAL_TEST\n")
    with pytest.raises(SupervisionError, match="P0_RECOVERY_EVALUATION_TRACE.jsonl"):
        publish_evidence(missing_trace, tmp_path / "final-trace-failure", CONTRACT_VERSION)

    missing_readonly = tmp_path / "missing-readonly"
    _write_base_outputs(missing_readonly)
    (missing_readonly / "P0_RECOVERY_EVALUATION_TRACE.jsonl").write_text("NON_FORMAL_TEST\n")
    with pytest.raises(SupervisionError, match="P0_READONLY_POSTRUN_VALIDATION.json"):
        publish_evidence(missing_readonly, tmp_path / "final-readonly-failure", CONTRACT_VERSION)


def test_v1_publication_does_not_require_v2_artifacts(tmp_path: Path):
    work = tmp_path / "work"
    final = tmp_path / "final"
    _write_base_outputs(work)
    publish_evidence(work, final, "P0_RECOVERY_CONTRACT_V1")
    assert not (final / V2_REQUIRED_OUTPUTS[0]).exists()


def test_v2_publication_checks_artifact_identity(tmp_path: Path):
    work = tmp_path / "work"
    final = tmp_path / "final"
    _write_base_outputs(work)
    identity = {
        "directive": "UMBRA-D-013H",
        "formal_execution_id": "non-formal-execution-001",
        "starting_commit": "cf29ac28b2e51a36f450df490e756344b85e6c78",
        "configuration_fingerprint": "config-hash",
        "formal_recovery_contract_version": CONTRACT_VERSION,
        "contract_fingerprint": CONTRACT_FINGERPRINT,
    }
    (work / "P0_READONLY_POSTRUN_VALIDATION.json").write_text(json.dumps(identity))
    (work / "P0_RECOVERY_EVALUATION_TRACE.jsonl").write_text(
        json.dumps({
            "record_type": "EVALUATOR_INIT",
            "directive": identity["directive"],
            "formal_execution_id": identity["formal_execution_id"],
            "starting_commit": identity["starting_commit"],
            "configuration_fingerprint": identity["configuration_fingerprint"],
            "verdict_namespace": "D013H",
            "contract_version": CONTRACT_VERSION,
            "contract_fingerprint": CONTRACT_FINGERPRINT,
        }) + "\n"
    )
    publish_evidence(work, final, CONTRACT_VERSION, identity=identity)
    assert (final / "P0_READONLY_POSTRUN_VALIDATION.json").exists()
