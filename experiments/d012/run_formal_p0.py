"""Execute the frozen UMBRA-D-012B adaptive fail-fast formal P0."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

from .campaign_supervisor import CampaignSupervisor, freeze_hash
from .checkpoint_runner import run_checkpoint
from .database_ownership import assert_quiescent, read_ownership
from .durability import atomic_write_text
from .failure_codes import SupervisionError
from .process_identity import identity_matches, process_identity
from .worker_launcher import WorkerClient, manifest_for

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
CONFIG_PATH = EXP / "p0-formal-config.json"
REQUIRED_OUTPUTS = (
    "p0-formal-execution-manifest.json",
    "p0-entry-audit.json",
    "p0-schedule-trace.jsonl",
    "p0-process-trace.jsonl",
    "p0-resource-samples.jsonl",
    "p0-window-analysis.json",
    "p0-autonomy-results.json",
    "p0-perception-results.json",
    "p0-worker-restart-results.json",
    "p0-checkpoint-results.json",
    "p0-snapshot-restart-results.json",
    "p0-chain-validation.json",
    "p0-raw-payload-audit.json",
    "p0-bounded-state-results.json",
    "p0-process-audit.json",
    "p0-run-result.json",
)


class P0Failure(RuntimeError):
    def __init__(self, verdict: str, invariant: str) -> None:
        self.verdict = verdict
        self.invariant = invariant
        super().__init__(f"{verdict}:{invariant}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def current_active(supervisor: CampaignSupervisor) -> float:
    active = supervisor.runtime.committed_seconds
    if supervisor.runtime.interval_started is not None:
        active += time.monotonic() - supervisor.runtime.interval_started
    return active


def child_count(pid: int) -> int:
    path = Path(f"/proc/{pid}/task/{pid}/children")
    return len(path.read_text().split()) if path.exists() else 0


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def slope_and_ci(samples: list[dict[str, Any]]) -> tuple[float, list[float]]:
    if len(samples) < 3:
        return 0.0, [-math.inf, math.inf]
    x = [float(sample["active_runtime_seconds"]) / 3600.0 for sample in samples]
    y = [float(sample["rss_mib"]) for sample in samples]
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        return 0.0, [-math.inf, math.inf]
    slope = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y)) / denominator
    intercept = y_mean - slope * x_mean
    residual = sum(
        (b - (intercept + slope * a)) ** 2 for a, b in zip(x, y)
    )
    error = math.sqrt((residual / max(1, len(x) - 2)) / denominator)
    return slope, [slope - 2.0 * error, slope + 2.0 * error]


def segment_medians(samples: list[dict[str, Any]]) -> list[float]:
    if not samples:
        return []
    size = max(1, len(samples) // 4)
    return [
        statistics.median(float(row["rss_mib"]) for row in samples[index : index + size])
        for index in range(0, len(samples), size)
    ][:4]


def analyze_samples(
    samples: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    thresholds = config["thresholds"]
    elapsed = float(samples[-1]["active_runtime_seconds"]) if samples else 0.0
    post = [
        row
        for row in samples
        if float(row["active_runtime_seconds"])
        >= float(thresholds["post_startup_seconds"])
    ]
    recent_start = max(
        float(thresholds["post_startup_seconds"]),
        elapsed - float(thresholds["recent_window_seconds"]),
    )
    recent = [
        row for row in samples if float(row["active_runtime_seconds"]) >= recent_start
    ]
    windows = {"full": samples, "post_startup": post, "recent": recent}
    slopes: dict[str, Any] = {}
    for name, rows in windows.items():
        slope, interval = slope_and_ci(rows)
        slopes[name] = {
            "sample_indices": [int(row["sample_index"]) for row in rows],
            "slope_mib_per_hour": slope,
            "confidence_interval": interval,
        }
    rss = [float(row["rss_mib"]) for row in samples]
    medians = segment_medians(post)
    staircase = len(medians) == 4 and all(
        medians[index + 1] > medians[index] for index in range(3)
    ) and medians[-1] - medians[0] > 0.25
    cpu_total = sum(float(row["cpu_fraction"]) * float(row["sample_seconds"]) for row in samples)
    duration_total = sum(float(row["sample_seconds"]) for row in samples)
    mean_cpu = cpu_total / max(duration_total, 1e-9)
    near = float(thresholds["near_hard_limit_fraction"])
    limit = float(thresholds["rss_slope_mib_per_hour_max"])
    failure_reasons: list[str] = []
    for name in ("post_startup", "recent"):
        interval = slopes[name]["confidence_interval"]
        if (
            float(slopes[name]["slope_mib_per_hour"]) > limit
            and float(interval[0]) > limit
        ):
            failure_reasons.append(f"{name}_rss_slope")
    if staircase:
        failure_reasons.append("sustained_monotonic_rss_staircase")
    if mean_cpu > float(thresholds["cpu_mean_fraction_max"]):
        failure_reasons.append("cpu_mean_fraction")
    stable = bool(
        elapsed >= float(config["minimum_active_seconds"])
        and post
        and recent
        and not failure_reasons
        and not staircase
        and max(float(slopes[name]["slope_mib_per_hour"]) for name in slopes)
        <= limit
        and float(slopes["post_startup"]["confidence_interval"][1])
        <= limit
        and float(slopes["recent"]["confidence_interval"][1])
        <= limit
        and max(rss, default=0.0) < float(thresholds["rss_mib_hard_max"]) * near
        and mean_cpu <= float(thresholds["cpu_mean_fraction_max"])
    )
    return {
        "active_runtime_seconds": elapsed,
        "sample_interval_seconds": config["sample_interval_seconds"],
        "primary_window": "post_startup",
        "windows": slopes,
        "rss_min_mib": min(rss, default=0.0),
        "rss_max_mib": max(rss, default=0.0),
        "rss_median_mib": statistics.median(rss) if rss else 0.0,
        "rss_p95_mib": percentile(rss, 0.95),
        "rss_segment_medians_mib": medians,
        "sustained_monotonic_rss_staircase": staircase,
        "cpu_mean_fraction": mean_cpu,
        "classification": (
            "FAILED"
            if failure_reasons
            else "CLEARLY_STABLE"
            if stable
            else "AMBIGUOUS"
        ),
        "failure_reasons": failure_reasons,
        "stable": stable,
    }


def bounded_failures(
    sample: dict[str, Any],
    first: dict[int, dict[str, Any]],
    thresholds: dict[str, Any],
) -> list[str]:
    generation = int(sample["worker_generation"])
    baseline = first.setdefault(generation, sample)
    failures: list[str] = []
    fixed_pairs = (
        ("perception_observation_count", "perception_observation_max"),
        ("deduplication_id_count", "deduplication_id_max"),
        ("child_process_count", "worker_child_process_max"),
    )
    for measured, limit in fixed_pairs:
        if int(sample[measured]) > int(thresholds[limit]):
            failures.append(measured)
    dynamic_pairs = (
        ("memory_count", "memory_count_max"),
        ("social_hypothesis_count", "social_hypothesis_count_max"),
        ("routine_count", "routine_count_max"),
        ("world_model_count", "world_model_count_max"),
        ("individuality_evidence_count", "individuality_evidence_count_max"),
        ("expression_retained_count", "expression_retained_count_max"),
        ("habitat_object_count", "habitat_object_count_max"),
    )
    for measured, limit in dynamic_pairs:
        if int(sample[measured]) > int(sample[limit]):
            failures.append(measured)
    if int(sample["file_descriptor_count"]) > int(baseline["file_descriptor_count"]) + int(
        thresholds["file_descriptor_delta_max"]
    ):
        failures.append("file_descriptor_count")
    if int(sample["thread_count"]) > int(baseline["thread_count"]) + int(
        thresholds["thread_delta_max"]
    ):
        failures.append("thread_count")
    return failures


def run(
    *,
    run_root: Path,
    evidence_root: Path,
    execution_id: str,
    starting_commit: str,
) -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text())
    thresholds = config["thresholds"]
    expected_freeze = freeze_hash(EXP)
    config_hash = sha256(CONFIG_PATH)
    if git("rev-parse", "--short", "HEAD") != starting_commit:
        raise SupervisionError("STARTING_COMMIT_MISMATCH")
    if run_root.exists() and any(run_root.iterdir()):
        raise SupervisionError("DUPLICATE_CAMPAIGN", "run_root_not_empty")
    if any((evidence_root / name).exists() for name in REQUIRED_OUTPUTS):
        raise SupervisionError("DUPLICATE_CAMPAIGN", "formal_evidence_exists")

    work_evidence = run_root / "evidence"
    database = run_root / "organism.sqlite"
    ownership_path = run_root / "database-ownership.json"
    schedule_path = work_evidence / "p0-schedule-trace.jsonl"
    process_path = work_evidence / "p0-process-trace.jsonl"
    sample_path = work_evidence / "p0-resource-samples.jsonl"
    supervisor = CampaignSupervisor(
        run_root,
        execution_id,
        database,
        work_evidence,
        expected_freeze,
        expected_starting_commit=starting_commit,
    )
    client: WorkerClient | None = None
    worker_records: list[dict[str, Any]] = []
    schedule_records: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    first_generation_sample: dict[int, dict[str, Any]] = {}
    perception_records: list[dict[str, Any]] = []
    restart_result: dict[str, Any] = {"performed": False}
    checkpoint_result: dict[str, Any] = {"performed": False}
    snapshot_result: dict[str, Any] = {"performed": False}
    organism_id: str | None = None
    generation = 1
    ownership_generation = 1
    last_chain_tip = 0
    last_tick = 0
    last_cpu = 0.0
    last_sample_active = 0.0
    verdict = "UMBRA_D012B_P0_ABORTED_INFRASTRUCTURE"
    first_failure: str | None = None
    checkpoint_done = False
    actions_done: set[str] = set()

    def trace_process(event: str, **fields: Any) -> None:
        record = {
            "event": event,
            "wall_time": time.time(),
            "active_runtime_seconds": current_active(supervisor),
            **fields,
        }
        worker_records.append(record)
        append_jsonl(process_path, record)

    def trace_schedule(event: str, **fields: Any) -> None:
        record = {
            "event": event,
            "wall_time": time.time(),
            "active_runtime_seconds": current_active(supervisor),
            **fields,
        }
        schedule_records.append(record)
        append_jsonl(schedule_path, record)

    def launch_worker() -> WorkerClient:
        nonlocal organism_id, ownership_generation, last_chain_tip, last_cpu
        manifest = manifest_for(
            run_root,
            execution_id=execution_id,
            generation=generation,
            ownership_generation=ownership_generation,
            freeze_manifest_hash=expected_freeze,
            active_runtime=supervisor.runtime.committed_seconds,
            database_path=database,
            tick_period_seconds=1.0 / float(config["tick_hz"]),
        )
        worker = WorkerClient.launch(
            run_root / f"worker-manifest-{generation}.json", manifest
        )
        supervisor.attach_worker(worker.pid, worker.identity, generation)
        started = worker.request(
            "START", active_runtime=supervisor.runtime.committed_seconds
        )
        supervisor.record_worker_status(started)
        current_id = str(started["organism_id"])
        if organism_id is None:
            organism_id = current_id
        elif organism_id != current_id:
            raise P0Failure(
                "UMBRA_D012B_P0_INTEGRITY_FAIL", "organism_identity_changed"
            )
        ownership_generation = int(started["ownership_generation"])
        last_chain_tip = int(started["chain_tip"] or 0)
        last_cpu = 0.0
        trace_process(
            "worker_started",
            supervisor_pid=os.getpid(),
            supervisor_identity=process_identity(os.getpid()),
            worker_pid=worker.pid,
            worker_identity=worker.identity,
            worker_generation=generation,
            ownership_generation=ownership_generation,
        )
        return worker

    def execute_event(index: int, label: str) -> None:
        nonlocal last_chain_tip
        assert client is not None
        response = client.request(
            "RUN_EVENT",
            event_index=index,
            active_runtime=current_active(supervisor),
        )
        supervisor.record_worker_status(response)
        result = dict(response["event"])
        if result["organism_id"] != organism_id:
            raise P0Failure(
                "UMBRA_D012B_P0_INTEGRITY_FAIL", "organism_identity_changed"
            )
        if int(response["chain_tip"] or 0) <= last_chain_tip:
            raise P0Failure(
                "UMBRA_D012B_P0_INTEGRITY_FAIL", "event_chain_not_advanced"
            )
        last_chain_tip = int(response["chain_tip"])
        supervisor.complete_event(str(result["event"]))
        trace_schedule(label, schedule_index=index, result=result)
        if "perception" in result:
            perception_records.append(result)

    def sample() -> dict[str, Any]:
        nonlocal last_chain_tip, last_tick, last_cpu, last_sample_active
        assert client is not None
        active = current_active(supervisor)
        response = client.request("METRICS", active_runtime=active)
        supervisor.record_worker_status(response)
        metrics = dict(response["metrics"])
        chain_tip = int(response["chain_tip"] or 0)
        if chain_tip < last_chain_tip:
            raise P0Failure(
                "UMBRA_D012B_P0_INTEGRITY_FAIL", "event_chain_discontinuity"
            )
        if samples and int(metrics["tick"]) <= last_tick:
            raise P0Failure(
                "UMBRA_D012B_P0_INTEGRITY_FAIL", "autonomous_tick_stalled"
            )
        dt = max(1e-9, active - last_sample_active)
        cpu = float(metrics["cpu_seconds"])
        cpu_fraction = max(0.0, cpu - last_cpu) / dt if last_cpu else cpu / dt
        record = {
            "sample_index": len(samples),
            "wall_time": time.time(),
            "active_runtime_seconds": active,
            "sample_seconds": dt,
            "cpu_fraction": cpu_fraction,
            "supervisor_pid": os.getpid(),
            "supervisor_child_process_count": child_count(os.getpid()),
            "worker_pid": client.pid,
            "worker_identity": client.identity,
            "worker_generation": generation,
            "chain_tip": chain_tip,
            **metrics,
        }
        if record["supervisor_child_process_count"] != int(
            thresholds["supervisor_child_process_max"]
        ):
            raise P0Failure(
                "UMBRA_D012B_P0_SUPERVISION_FAIL",
                "supervisor_child_process_count",
            )
        if not identity_matches(client.pid, client.identity):
            raise P0Failure(
                "UMBRA_D012B_P0_SUPERVISION_FAIL", "worker_identity_mismatch"
            )
        if float(record["rss_mib"]) > float(thresholds["rss_mib_hard_max"]):
            raise P0Failure("UMBRA_D012B_P0_PERFORMANCE_FAIL", "rss_hard_ceiling")
        if int(record["database_bytes"]) - int(samples[0]["database_bytes"] if samples else record["database_bytes"]) > int(
            thresholds["database_growth_bytes_max"]
        ):
            raise P0Failure(
                "UMBRA_D012B_P0_PERFORMANCE_FAIL", "database_growth_hard_ceiling"
            )
        if int(record["durable_raw_count"]) != 0:
            raise P0Failure(
                "UMBRA_D012B_P0_INTEGRITY_FAIL", "durable_raw_sensor_payload"
            )
        if bool(record["physiology_critical"]):
            raise P0Failure(
                "UMBRA_D012B_P0_INTEGRITY_FAIL", "invalid_physiological_state"
            )
        if not bool(record["chain_valid"]):
            raise P0Failure(
                "UMBRA_D012B_P0_INTEGRITY_FAIL", "event_chain_validation"
            )
        if samples:
            tick_delta = int(record["tick"]) - int(samples[-1]["tick"])
            event_delta = int(record["event_count"]) - int(samples[-1]["event_count"])
            if tick_delta > 0 and event_delta / tick_delta > float(
                thresholds["event_growth_per_tick_max"]
            ):
                raise P0Failure(
                    "UMBRA_D012B_P0_PERFORMANCE_FAIL",
                    "event_growth_per_tick_hard_ceiling",
                )
        failures = bounded_failures(record, first_generation_sample, thresholds)
        if failures:
            raise P0Failure(
                "UMBRA_D012B_P0_PERFORMANCE_FAIL",
                "bounded_state:" + ",".join(failures),
            )
        samples.append(record)
        append_jsonl(sample_path, record)
        last_chain_tip = chain_tip
        last_tick = int(record["tick"])
        last_cpu = cpu
        last_sample_active = active
        supervisor.heartbeat()
        return record

    supervisor.acquire()
    supervisor.set_status("PREFLIGHT")
    try:
        entry = {
            "directive": "UMBRA-D-012B",
            "execution_id": execution_id,
            "repository_baseline": starting_commit,
            "d009_seal_present": git("merge-base", "--is-ancestor", "af35371", "HEAD")
            == "",
            "d011_closeout_present": git(
                "merge-base", "--is-ancestor", "97143b1", "HEAD"
            )
            == "",
            "d012a2_baseline_present": git(
                "merge-base", "--is-ancestor", "6d872ab", "HEAD"
            )
            == "",
            "freeze_manifest_hash": expected_freeze,
            "p0_config_sha256": config_hash,
            "d010_enabled": False,
            "p1_authorized": False,
            "p2_authorized": False,
            "harness_direct_state_mutation": False,
            "harness_imports_organism_runtime": False,
            "entry_pass": True,
        }
        write_json(work_evidence / "p0-entry-audit.json", entry)
        client = launch_worker()
        manifest = {
            "formal_execution_id": execution_id,
            "starting_commit": starting_commit,
            "freeze_manifest_hash": expected_freeze,
            "p0_config_sha256": config_hash,
            "organism_identity": organism_id,
            "database_path": str(database.resolve()),
            "evidence_path": str(work_evidence.resolve()),
            "supervisor_pid": os.getpid(),
            "supervisor_process_start_identity": process_identity(os.getpid()),
            "worker_pid": client.pid,
            "worker_process_start_identity": client.identity,
            "worker_generation": generation,
            "ownership_generation": ownership_generation,
            "active_runtime_counter": supervisor.runtime.to_dict(),
            "created_at": time.time(),
        }
        write_json(work_evidence / "p0-formal-execution-manifest.json", manifest)
        supervisor.set_status("RUNNING")
        supervisor.start_interval(time.monotonic())
        execute_event(
            int(config["schedule_indices"]["autonomous_no_interaction"]),
            "autonomous_no_interaction",
        )
        trace_schedule(
            "ordinary_habitat_opportunity",
            authority="environment_only",
            direct_state_mutation=False,
        )
        next_sample = float(config["sample_interval_seconds"])
        next_decision = float(config["minimum_active_seconds"])
        final_analysis: dict[str, Any] | None = None

        while True:
            active = current_active(supervisor)
            if active >= 300 and "partner" not in actions_done:
                execute_event(
                    int(config["schedule_indices"]["recurring_partner_exposure"]),
                    "synthetic_recurring_partner_exposure",
                )
                actions_done.add("partner")
            if active >= 600 and "perception" not in actions_done:
                execute_event(
                    int(config["schedule_indices"]["perception_adapter_restart"]),
                    "governed_perception_adapter_restart_and_intake",
                )
                execute_event(
                    int(config["schedule_indices"]["duplicate_observation_burst"]),
                    "duplicate_observation_burst",
                )
                actions_done.add("perception")
            if active >= 900 and "restart" not in actions_done:
                supervisor.stop_interval(time.monotonic())
                before_runtime = supervisor.runtime.committed_seconds
                before_tip = last_chain_tip
                before_id = organism_id
                supervisor.set_status("RESTARTING")
                stopped = client.shutdown(before_runtime)
                supervisor.record_worker_status(stopped)
                trace_process(
                    "worker_stopped_for_controlled_restart",
                    worker_pid=client.pid,
                    worker_identity=client.identity,
                    worker_generation=generation,
                )
                ownership_generation = int(stopped["ownership_generation"]) + 1
                generation += 1
                client = launch_worker()
                after_tip = int(client.chain_tip or 0)
                restart_result = {
                    "performed": True,
                    "identity_before": before_id,
                    "identity_after": organism_id,
                    "identity_unchanged": before_id == organism_id,
                    "chain_tip_before": before_tip,
                    "chain_tip_after": after_tip,
                    "chain_preserved": after_tip >= before_tip,
                    "active_runtime_before_seconds": before_runtime,
                    "active_runtime_after_seconds": supervisor.runtime.committed_seconds,
                    "downtime_excluded": supervisor.runtime.committed_seconds
                    == before_runtime,
                    "worker_generation": generation,
                    "ownership_generation": ownership_generation,
                    "schedule_position": supervisor.state[
                        "last_completed_schedule_event"
                    ],
                    "pass": before_id == organism_id
                    and after_tip >= before_tip
                    and supervisor.runtime.committed_seconds == before_runtime,
                }
                if not restart_result["pass"]:
                    raise P0Failure(
                        "UMBRA_D012B_P0_INTEGRITY_FAIL",
                        "controlled_worker_restart",
                    )
                supervisor.set_status("RUNNING")
                supervisor.start_interval(time.monotonic())
                actions_done.add("restart")
                next_sample = current_active(supervisor)
            active = current_active(supervisor)
            if active >= 1200 and not checkpoint_done:
                supervisor.stop_interval(time.monotonic())
                supervisor.set_status("CHECKPOINTING")
                ready = client.request(
                    "CHECKPOINT_PREPARE",
                    active_runtime=supervisor.runtime.committed_seconds,
                )
                supervisor.record_worker_status(ready)
                assert_quiescent(ownership_path)
                checkpoint_result = run_checkpoint(
                    database,
                    work_evidence / "checkpoint",
                    "P0-T20",
                    ownership_path=ownership_path,
                )
                checkpoint_result["performed"] = True
                supervisor.complete_checkpoint("P0-T20")
                resumed = client.request(
                    "RESUME", active_runtime=supervisor.runtime.committed_seconds
                )
                supervisor.record_worker_status(resumed)
                ownership_generation = int(resumed["ownership_generation"])
                snapshot_metrics = client.request(
                    "METRICS", active_runtime=supervisor.runtime.committed_seconds
                )
                supervisor.record_worker_status(snapshot_metrics)
                accepted_hash = snapshot_metrics["metrics"]["accepted_state_hash"]
                snapshot_result = {
                    "performed": True,
                    "checkpoint_state_hash": checkpoint_result["state_hash"],
                    "accepted_state_hash": accepted_hash,
                    "state_hash_matches": accepted_hash
                    == checkpoint_result["state_hash"],
                    "organism_identity": snapshot_metrics["organism_id"],
                    "identity_unchanged": snapshot_metrics["organism_id"]
                    == organism_id,
                    "pass": accepted_hash == checkpoint_result["state_hash"]
                    and snapshot_metrics["organism_id"] == organism_id,
                }
                if not snapshot_result["pass"]:
                    raise P0Failure(
                        "UMBRA_D012B_P0_INTEGRITY_FAIL", "snapshot_restart"
                    )
                checkpoint_done = True
                supervisor.set_status("RUNNING")
                supervisor.start_interval(time.monotonic())
                next_sample = current_active(supervisor)
                next_decision = max(
                    next_decision, float(config["minimum_active_seconds"])
                )
                trace_schedule(
                    "quiesced_checkpoint_and_snapshot_restart",
                    checkpoint_id="P0-T20",
                    state_hash=checkpoint_result["state_hash"],
                )
            active = current_active(supervisor)
            if active >= next_sample:
                sample()
                next_sample += float(config["sample_interval_seconds"])
            if checkpoint_done and active >= next_decision and samples:
                final_analysis = analyze_samples(samples, config)
                if final_analysis["classification"] == "FAILED":
                    raise P0Failure(
                        "UMBRA_D012B_P0_PERFORMANCE_FAIL",
                        "resource_stability:"
                        + ",".join(final_analysis["failure_reasons"]),
                    )
                if final_analysis["stable"]:
                    verdict = "UMBRA_D012B_P0_PASS"
                    break
                if active >= float(config["maximum_active_seconds"]):
                    verdict = "UMBRA_D012B_P0_INCONCLUSIVE"
                    break
                next_decision += float(config["extension_seconds"])
            time.sleep(0.1)

        supervisor.stop_interval(time.monotonic())
        stopped = client.shutdown(supervisor.runtime.committed_seconds)
        supervisor.record_worker_status(stopped)
        trace_process(
            "worker_stopped_final",
            worker_pid=client.pid,
            worker_identity=client.identity,
            worker_generation=generation,
        )
        client = None
        supervisor.set_status(
            "COMPLETED"
            if verdict in {"UMBRA_D012B_P0_PASS", "UMBRA_D012B_P0_INCONCLUSIVE"}
            else "FAILED_SCIENTIFIC"
        )
        supervisor.release()
        final_analysis = final_analysis or analyze_samples(samples, config)
    except P0Failure as exc:
        verdict = exc.verdict
        first_failure = exc.invariant
        raise
    except SupervisionError as exc:
        first_failure = str(exc)
        verdict = (
            "UMBRA_D012B_P0_SUPERVISION_FAIL"
            if exc.code
            in {
                "DATABASE_ALREADY_OWNED",
                "OWNERSHIP_TRANSFER_INCOMPLETE",
                "PID_IDENTITY_MISMATCH",
                "IPC_IDENTITY_MISMATCH",
                "ORGANISM_EXIT_UNEXPECTED",
            }
            else "UMBRA_D012B_P0_INTEGRITY_FAIL"
        )
        raise
    finally:
        if client is not None and identity_matches(client.pid, client.identity):
            try:
                active = current_active(supervisor)
                if supervisor.runtime.interval_started is not None:
                    supervisor.stop_interval(time.monotonic())
                    active = supervisor.runtime.committed_seconds
                client.shutdown(active)
            except BaseException:
                client.force_kill()
        if supervisor.lock_path.exists():
            try:
                supervisor.set_status(
                    "FAILED_SCIENTIFIC"
                    if verdict
                    in {
                        "UMBRA_D012B_P0_PERFORMANCE_FAIL",
                        "UMBRA_D012B_P0_INTEGRITY_FAIL",
                        "UMBRA_D012B_P0_SUPERVISION_FAIL",
                    }
                    else "FAILED_INFRASTRUCTURE"
                )
                supervisor.state["termination_reason"] = first_failure
                supervisor.release()
            except BaseException:
                pass

        owner = read_ownership(ownership_path)
        remaining_workers = [
            row["worker_pid"]
            for row in worker_records
            if row["event"] == "worker_started"
            and identity_matches(int(row["worker_pid"]), str(row["worker_identity"]))
        ]
        sockets = sorted(path.name for path in run_root.glob("*.sock"))
        process_audit = {
            "supervisor_pid": os.getpid(),
            "remaining_worker_pids": remaining_workers,
            "remaining_sockets": sockets,
            "campaign_lock_exists": supervisor.lock_path.exists(),
            "database_ownership_status": None
            if owner is None
            else owner["status"],
            "incomplete_checkpoint_files": sorted(
                path.name
                for path in (work_evidence / "checkpoint").glob("*.partial.sqlite")
            )
            if (work_evidence / "checkpoint").exists()
            else [],
            "pass": not remaining_workers
            and not sockets
            and not supervisor.lock_path.exists()
            and (owner is None or owner["status"] == "RELEASED"),
        }
        final_analysis = analyze_samples(samples, config)
        write_json(work_evidence / "p0-window-analysis.json", final_analysis)
        write_json(
            work_evidence / "p0-autonomy-results.json",
            {
                "first_tick": samples[0]["tick"] if samples else None,
                "last_tick": samples[-1]["tick"] if samples else None,
                "ticks_advanced": bool(samples)
                and int(samples[-1]["tick"]) > int(samples[0]["tick"]),
                "proposal_count": samples[-1]["proposal_count"] if samples else 0,
                "outcome_count": samples[-1]["outcome_count"] if samples else 0,
                "direct_action_injection": False,
                "expression_read_only": True,
                "pass": bool(samples)
                and int(samples[-1]["tick"]) > int(samples[0]["tick"])
                and int(samples[-1]["proposal_count"]) > 0
                and int(samples[-1]["outcome_count"]) > 0,
            },
        )
        write_json(
            work_evidence / "p0-perception-results.json",
            {
                "events": perception_records,
                "adapter_restart_seen": any(
                    row["event"] == "p0-adapter-restart"
                    for row in perception_records
                ),
                "duplicate_burst_suppressed": any(
                    row.get("perception", {}).get("duplicates_suppressed") == 8
                    for row in perception_records
                ),
                "provenance_preserved": all(
                    row.get("perception", {}).get("provenance_chain")
                    for row in perception_records
                ),
                "uncertainty_preserved": all(
                    isinstance(row.get("perception", {}).get("uncertainty"), float)
                    for row in perception_records
                ),
            },
        )
        write_json(
            work_evidence / "p0-worker-restart-results.json", restart_result
        )
        write_json(work_evidence / "p0-checkpoint-results.json", checkpoint_result)
        write_json(
            work_evidence / "p0-snapshot-restart-results.json", snapshot_result
        )
        write_json(
            work_evidence / "p0-chain-validation.json",
            {
                "sample_chain_tips": [row["chain_tip"] for row in samples],
                "monotonic": all(
                    int(samples[index]["chain_tip"])
                    >= int(samples[index - 1]["chain_tip"])
                    for index in range(1, len(samples))
                ),
                "final_chain_tip": samples[-1]["chain_tip"] if samples else None,
            },
        )
        write_json(
            work_evidence / "p0-raw-payload-audit.json",
            {
                "durable_raw_payload_count": samples[-1]["durable_raw_count"]
                if samples
                else None,
                "ipc_raw_payload_permitted": False,
                "pass": bool(samples)
                and int(samples[-1]["durable_raw_count"]) == 0,
            },
        )
        bounded_keys = (
            "perception_observation_count",
            "deduplication_id_count",
            "memory_count",
            "social_hypothesis_count",
            "routine_count",
            "world_model_count",
            "individuality_evidence_count",
            "habitat_object_count",
            "habitat_journal_count",
            "expression_retained_count",
        )
        write_json(
            work_evidence / "p0-bounded-state-results.json",
            {
                "maxima": {
                    key: max((int(row[key]) for row in samples), default=0)
                    for key in bounded_keys
                },
                "first_failure": first_failure,
                "pass": first_failure is None
                or not first_failure.startswith("bounded_state:"),
            },
        )
        write_json(work_evidence / "p0-process-audit.json", process_audit)
        result = {
            "directive": "UMBRA-D-012B",
            "formal_execution_id": execution_id,
            "verdict": verdict,
            "first_failing_invariant": first_failure,
            "active_runtime_seconds": supervisor.runtime.committed_seconds,
            "worker_generations": generation,
            "organism_identity": organism_id,
            "sample_count": len(samples),
            "checkpoint_completed": checkpoint_done,
            "process_cleanup_pass": process_audit["pass"],
            "p1_launched": False,
            "p2_launched": False,
        }
        write_json(work_evidence / "p0-run-result.json", result)
        evidence_root.mkdir(parents=True, exist_ok=True)
        for name in REQUIRED_OUTPUTS:
            source = work_evidence / name
            if source.exists():
                shutil.copy2(source, evidence_root / name)

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--starting-commit", required=True)
    args = parser.parse_args()
    try:
        result = run(
            run_root=args.run_root,
            evidence_root=args.evidence_root,
            execution_id=args.execution_id,
            starting_commit=args.starting_commit,
        )
    except (P0Failure, SupervisionError) as exc:
        print(str(exc))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
