"""Copy-only retrospective audit; never creates or resumes an organism.

This is a new audit, not a modification of any frozen scientific verdict.
Missing evidence is BLOCKED. Structurally valid but corrupted contents FAIL.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.d012.readonly_validation import validate_read_only
from experiments.as018.full_config import config, fingerprint
from tools.as017_evidence import (
    iter_jsonl, publish_json_once, stream_sha256,
    validate_sqlite_copy, verify_trace_row_hash,
)
from tools.as017_validate_linkage_v2 import validate_linkage_v2
from umbra_core.physiology import Physiology

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "246e1ac574eff96ddc68b3e4cd1ff17789936449"
LOCK_SHA = "1354af3826402ef471ecc641b25b4852305ab32421f45904f4ab9340b1ec3019"
MANIFEST_SHA = "8389f413e0561f5c991de0ef1c468e1b4e845aec6989174d021673da6bbcbe5b"
CATEGORIES = {"ROBUST_NOW", "BOUNDED_RECOVERY_OPPORTUNITY", "MAY_ROUTE", "UNKNOWN_ROUTE"}


def bounded_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        raw = handle.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("metadata_size_exceeded")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("metadata_not_object")
    return result


def validate_database_copy(
    source: Path, expected_hash: str, expected_tick: int, expected_seed: int,
    *, expected_identity: dict[str, Any] | None = None,
    max_hot_tail: int = 32768, sidecar_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Recompute commitments, payload/event/checkpoint/snapshot hashes on a copy.

    Caller must provide a quiescent source. WAL bytes are preserved together
    and must have independent bindings; historical originals are never opened
    by SQLite. Consistency is not proof of unknown pre-birth provenance.
    """
    failures: list[str] = []
    report: dict[str, Any] = {"failures": failures, "source": str(source),
                              "historical_birth_identity_bound": expected_identity is not None}
    try:
        before = stream_sha256(source)
        if before != expected_hash:
            failures.append("database_hash_mismatch")
        with tempfile.TemporaryDirectory(prefix="umbra-copy-audit-") as scratch:
            isolated = Path(scratch) / source.name
            shutil.copyfile(source, isolated)
            for suffix in ("-wal", "-shm", "-journal"):
                sidecar = Path(str(source) + suffix)
                if sidecar.exists():
                    digest = stream_sha256(sidecar)
                    if (sidecar_hashes or {}).get(suffix) != digest:
                        failures.append(f"sidecar_binding_missing_or_mismatched:{suffix}")
                    shutil.copyfile(sidecar, Path(str(isolated) + suffix))
                    if digest != stream_sha256(sidecar):
                        failures.append(f"sidecar_changed_during_copy:{suffix}")
            if before != stream_sha256(source) or before != stream_sha256(isolated):
                failures.append("source_or_copy_changed")
            connection = sqlite3.connect(isolated)
            try:
                hot_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            finally:
                connection.close()
            if hot_count > max_hot_tail:
                raise ValueError("hot_tail_limit_exceeded")
            report["sqlite"] = validate_sqlite_copy(isolated)
            if report["sqlite"] != {"integrity_check": "ok", "foreign_key_check_rows": 0}:
                failures.append("sqlite_integrity_or_foreign_keys")
            report["cryptographic_chain"] = validate_read_only(isolated)
            connection = sqlite3.connect(f"file:{isolated}?mode=ro", uri=True)
            try:
                identity = json.loads(connection.execute("SELECT record_json FROM identity").fetchone()[0])
                report["identity"] = identity
                if expected_identity is not None and identity != expected_identity:
                    failures.append("birth_identity_mismatch")
                snapshots = connection.execute(
                    "SELECT agent_id, sequence, monotonic_time, state_json FROM snapshots ORDER BY sequence DESC, rowid DESC"
                )
                terminal = snapshots.fetchone()
                if terminal is None:
                    raise ValueError("terminal_snapshot_missing")
                state = json.loads(terminal[3])
                if terminal[2] != expected_tick or state.get("tick") != expected_tick:
                    failures.append("terminal_tick_mismatch")
                if state.get("seed") != expected_seed:
                    failures.append("snapshot_seed_mismatch")
                if terminal[0] != identity["agent_id"] or state.get("identity") != identity:
                    failures.append("snapshot_identity_mismatch")
                if terminal[1] != report["cryptographic_chain"]["max_event_sequence"]:
                    failures.append("snapshot_not_at_ledger_tip")
                if Physiology.from_state(state["physiology"]).critical_any():
                    failures.append("terminal_critical_physiology")
                for table in ("events", "snapshots", "ledger_checkpoints"):
                    mismatches = connection.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE agent_id != ?", (identity["agent_id"],)
                    ).fetchone()[0]
                    if mismatches:
                        failures.append(f"{table}_identity_mismatch")
                report["terminal_tick"] = state["tick"]
                report["hot_tail_events"] = hot_count
            finally:
                connection.close()
        if before != stream_sha256(source):
            failures.append("source_changed_during_audit")
        report["source_sha256"] = before
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        failures.append(f"content_validation:{type(exc).__name__}:{exc}")
    report["verdict"] = "PASS" if not failures else "FAIL"
    return report


def validate_trace_scope(path: Path, expected_tick: int) -> dict[str, Any]:
    """Exact tick coverage and RRE schema/authority checks, independently of linkage.

    Schema validation does not prove a historical envelope's prediction.
    Heading numerical correctness needs contemporaneous orientation evidence.
    """
    failures: list[str] = []
    rows = rre_rows = 0
    try:
        for row in iter_jsonl(path):
            rows += 1
            if rows > expected_tick:
                failures.append("trace_horizon_exceeded")
                break  # explicit FAIL, never silent acceptance truncation
            if type(row.get("tick")) is not int or row["tick"] != rows:
                failures.append(f"noncontiguous_tick:{rows}")
            if not verify_trace_row_hash(row):
                failures.append(f"row_hash:{rows}")
            physiology = row.get("physiology", {})
            for dimension in ("energy", "fatigue", "integrity", "stimulation"):
                value = physiology.get(dimension)
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                    failures.append(f"physiology_missing_or_invalid:{rows}:{dimension}")
            kernel = row.get("viability_kernel")
            if kernel is None:
                continue  # ordinary roots do not require an active envelope
            if not isinstance(kernel, dict):
                failures.append(f"kernel_invalid:{rows}")
                continue
            envelope = kernel.get("recovery_reachability_envelope")
            if not isinstance(envelope, dict):
                failures.append(f"active_kernel_rre_unavailable:{rows}")
                continue
            rre_rows += 1
            baseline = envelope.get("baseline", {})
            if (
                envelope.get("schema") != "AS018_RECOVERY_REACHABILITY_FILTER_V1"
                or envelope.get("action_authority") is not False
                or envelope.get("hidden_truth_fields") != 0
                or type(envelope.get("activation")) is not bool
                or baseline.get("schema") != "AS018_RECOVERY_REACHABILITY_ENVELOPE_V1"
                or baseline.get("status") not in CATEGORIES
                or baseline.get("robust_now") is not False
                or type(baseline.get("organism_tick")) is not int
                or baseline.get("organism_tick") != row.get("active_ticks")
            ):
                failures.append(f"rre_contract_invalid:{rows}")
            if envelope.get("activation") and (
                baseline.get("status") != "BOUNDED_RECOVERY_OPPORTUNITY"
                or baseline.get("reserve_threatened") is not True
            ):
                failures.append(f"unsupported_reserve_activation:{rows}")
        if rows != expected_tick:
            failures.append("trace_horizon_mismatch")
    except (OSError, ValueError, TypeError) as exc:
        failures.append(f"trace_validation:{type(exc).__name__}:{exc}")
    return {"verdict": "PASS" if not failures else "FAIL", "rows": rows,
            "rre_rows": rre_rows, "failures": failures,
            "numerical_heading_verification": "NOT_ESTABLISHED_BY_SCHEMA_CHECK",
            "recovery_prediction_verification": "NOT_ESTABLISHED_BY_SCHEMA_CHECK"}


def validate_accounting(path: Path, expected_cases: dict[str, tuple[str, int, int]]) -> dict[str, Any]:
    """Check individual durable starts, stage order and each exported artifact.

    The frozen implementation exports files before LOCALLY_VALIDATED; that
    order is accepted here, but never confused with case acceptance.
    """
    failures = []
    required = ("REGISTERED", "STARTED", "EXECUTION_FINISHED", "VALIDATION_STARTED",
                "LOCALLY_VALIDATED", "CASE_FINISHED")
    progress = {case_id: [] for case_id in expected_cases}
    artifacts: dict[str, dict[str, str]] = {case_id: {} for case_id in expected_cases}
    case_result_hashes: dict[str, str] = {}
    counts: Counter[str] = Counter()
    latest: dict[str, str] = {}
    records = 0
    journal_status = "VALID"
    journal_error = None
    try:
        for row in iter_jsonl(path):
            records += 1
            if records > 4096:
                raise ValueError("journal_record_bound_exceeded")
            stage = row.get("stage")
            if stage not in {*required, "EXPORT_STARTED", "EXPORT_VERIFIED", "CASE_REJECTED",
                             "RUNNER_INTERRUPTED", "CAMPAIGN_FINISHED", "CAMPAIGN_STARTED"}:
                raise ValueError("journal_unknown_stage")
            counts[stage] += 1
            case_id = row.get("case_id")
            if case_id is None:
                continue  # campaign-level accounting is reconciled separately
            if case_id not in progress:
                raise ValueError("journal_unregistered_case")
            latest[case_id] = stage
            if stage in required:
                prefix = progress[case_id]
                if len(prefix) >= len(required) or stage != required[len(prefix)]:
                    failures.append(f"stage_order_or_duplicate:{case_id}:{stage}")
                prefix.append(stage)
            if stage == "STARTED":
                regime, index, seed = expected_cases[case_id]
                if (row.get("regime"), row.get("seed_index"), row.get("seed"), row.get("target_ticks")) != (regime, index, seed, 7200):
                    failures.append(f"started_binding:{case_id}")
            if stage == "EXPORT_VERIFIED":
                name, digest = row.get("artifact"), row.get("sha256")
                if name not in {"database", "compact_trace", "linkage_records", "linkage_summary", "case_result"} or not isinstance(digest, str) or len(digest) != 64:
                    failures.append(f"artifact_binding_invalid:{case_id}")
                elif name in artifacts[case_id]:
                    failures.append(f"duplicate_export:{case_id}:{name}")
                else:
                    artifacts[case_id][name] = digest
            if stage == "CASE_FINISHED":
                case_result_hashes[case_id] = row.get("case_result_sha256")
                names = {"database", "compact_trace", "linkage_records", "linkage_summary", "case_result"}
                if (set(row.get("required_artifacts", [])) != names
                        or set(artifacts[case_id]) != names
                        or artifacts[case_id].get("case_result") != row.get("case_result_sha256")):
                    failures.append(f"case_artifact_set_incomplete:{case_id}")
        for case_id in expected_cases:
            if tuple(progress[case_id]) != required:
                failures.append(f"incomplete_case_accounting:{case_id}")
    except (OSError, ValueError, TypeError) as exc:
        journal_status = "CORRUPTED"
        journal_error = str(exc)
        failures.append(f"journal_unreadable:{type(exc).__name__}:{exc}")
    summary = {"journal_status": journal_status, "journal_error": journal_error,
               "records": records, "expected_cases": len(expected_cases),
               "stage_counts": dict(counts), "case_states": latest,
               "incomplete_cases": [case_id for case_id in expected_cases
                                    if latest.get(case_id) != "CASE_FINISHED"]}
    if summary["journal_status"] != "VALID" or summary["incomplete_cases"]:
        failures.append("journal_corrupted_or_incomplete")
    return {"verdict": "PASS" if not failures else "FAIL", "failures": failures,
            "summary": summary, "artifact_hashes": artifacts, "case_result_hashes": case_result_hashes}


def audit_population(result: Path, journal: Path, work: Path) -> dict[str, Any]:
    manifest_path = ROOT / "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V2.json"
    lock_path = ROOT / "experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V2.json"
    manifest, lock = bounded_json(manifest_path), bounded_json(lock_path)
    expected = [(regime, index, seed) for regime in ("R0", "R1", "R2", "R3")
                for index, seed in enumerate(manifest["formal_regimes"][regime])]
    failures: list[str] = []
    missing = [str(path) for path in (result, journal, work) if not path.exists()]
    reports = [{"case_id": f"{regime}-{index:02d}-{seed}", "verdict": "BLOCKED",
                "regime": regime, "seed": seed, "reason": "detailed_evidence_unavailable"}
               for regime, index, seed in expected]
    payload: dict[str, Any] = {
        "schema": "UMBRA_RETROSPECTIVE_BASELINE_AUDIT_V1", "cases": reports,
        "missing": missing, "failures": failures, "expected_cases": 32,
        "frozen_verdict_rewritten": False, "formal_execution_performed": False,
        "validator_sha256": stream_sha256(Path(__file__)),
        "limitations": ["schema checks do not prove numerical headings or recovery predictions",
                        "missing historical evidence is not reconstructed"],
    }
    if stream_sha256(lock_path) != LOCK_SHA or stream_sha256(manifest_path) != MANIFEST_SHA:
        failures.append("frozen_contract_hash_mismatch")
    if missing:
        payload["verdict"] = "BLOCKED"
        return payload
    try:
        campaign = bounded_json(result)
        accounting = validate_accounting(journal, {f"{r}-{i:02d}-{s}": (r, i, s) for r, i, s in expected})
        stages = accounting["summary"]
        payload["accounting"] = accounting
        failures.extend(accounting["failures"])
        payload["journal"] = stages
        payload["result_sha256"] = stream_sha256(result)
        payload["journal_sha256"] = stream_sha256(journal)
        expected_ids = {row["case_id"] for row in reports}
        if (stages["journal_status"] != "VALID" or stages["incomplete_cases"]
                or set(stages["case_states"]) != expected_ids
                or stages["stage_counts"].get("STARTED") != 32
                or stages["stage_counts"].get("CASE_FINISHED") != 32):
            failures.append("journal_accounting_incomplete")
        for key in ("accepted_cases", "completed_runs", "formal_seed_consumption", "expected_runs"):
            if campaign.get(key) != 32:
                failures.append(f"population_accounting:{key}")
        for key in ("retries", "reseeds", "substitutions"):
            if campaign.get(key) != 0:
                failures.append(f"population_accounting:{key}")
        if campaign.get("candidate_commit") != CANDIDATE or campaign.get("seed_manifest_sha256") != MANIFEST_SHA:
            failures.append("population_source_binding")
        if campaign.get("terminal") != "AS018_FORMAL_POPULATION_PASS":
            failures.append("reported_population_not_pass")
        rows = campaign.get("rows", [])
        if [(row.get("regime"), row.get("seed_index"), row.get("seed")) for row in rows] != expected:
            failures.append("exact_ordered_population_mismatch")
            raise ValueError("case_order_or_count_invalid")
        for row, report in zip(rows, reports):
            regime, seed = report["regime"], report["seed"]
            case_id = report["case_id"]
            expected_config = fingerprint(config(seed, Path("unused.sqlite"), regime))
            frozen_config = dict(lock["configuration"]["fingerprints"][regime])
            frozen_config["seed"] = seed
            errors = []
            if row.get("configuration") != expected_config or expected_config != frozen_config:
                errors.append("configuration_binding_mismatch")
            for key, expected_value in (("candidate_commit", CANDIDATE), ("seed_manifest_sha256", MANIFEST_SHA),
                                        ("ticks", 7200), ("target_ticks", 7200), ("terminal", "completed"),
                                        ("scenario", {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}[regime]),
                                        ("critical_failure", None), ("first_no_safe_action", None),
                                        ("recovery_reachability_enabled", True)):
                if key not in row or row[key] != expected_value:
                    errors.append(f"case_binding:{key}")
            database = work / "exports/case-databases" / f"{regime}-{seed}.sqlite"
            trace = work / "exports/case-traces" / str(row.get("decision_trace_filename", "MISSING"))
            summary = work / "exports/certificate-linkage" / f"{case_id}.summary.json"
            records = work / "exports/certificate-linkage" / f"{case_id}.jsonl"
            case_result = work / "exports/case-results" / f"{case_id}.json"
            if any(not path.is_file() for path in (database, trace, summary, records, case_result)):
                report.update(verdict="BLOCKED", reason="required_artifacts_missing")
                failures.append(f"{case_id}:required_artifacts_missing")
                continue
            report["database"] = validate_database_copy(database, row.get("database_sha256", ""), 7200, seed)
            report["trace"] = validate_trace_scope(trace, 7200)
            bounded_json(summary)  # consumer's metadata read is now size-gated
            record_count = 0
            for _ in iter_jsonl(records):
                record_count += 1
                if record_count > 7200:
                    raise ValueError("linkage_record_bound_exceeded")
            if report["trace"]["verdict"] == "PASS":
                report["linkage"] = validate_linkage_v2(
                    summary, records, trace, CANDIDATE,
                    expected_summary_sha256=row.get("certificate_linkage_sha256", ""),
                    expected_trace_sha256=row.get("decision_trace_sha256", ""))
            else:
                report["linkage"] = {"verdict": "NOT_RUN", "failures": ["invalid_trace_prevents_linkage_audit"]}
            # A separately exported row must agree with the campaign before its
            # later-added case-result digest (the frozen writer adds it afterward).
            exported = bounded_json(case_result)
            row_compare = json.loads(json.dumps(row))
            row_compare.get("formal_acceptance", {}).pop("case_result_sha256", None)
            if exported != row_compare:
                errors.append("exported_case_row_mismatch")
            case_hash = stream_sha256(case_result)
            if case_hash != row.get("formal_acceptance", {}).get("case_result_sha256"):
                errors.append("case_result_hash_mismatch")
            actual_hashes = {"database": stream_sha256(database), "compact_trace": stream_sha256(trace),
                             "linkage_records": stream_sha256(records), "linkage_summary": stream_sha256(summary),
                             "case_result": case_hash}
            if accounting["artifact_hashes"].get(case_id) != actual_hashes:
                errors.append("journal_to_artifact_hash_binding_mismatch")
            for section in ("database", "trace", "linkage"):
                errors.extend(report[section]["failures"])
            report.update(verdict="FAIL" if errors else "PASS", failures=errors)
            failures.extend(f"{case_id}:{error}" for error in errors)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failures.append(f"audit_input:{type(exc).__name__}:{exc}")
    payload["verdict"] = "PASS" if not failures and all(r["verdict"] == "PASS" for r in reports) else "FAIL"
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit_population(args.result, args.journal, args.work)
    digest = publish_json_once(args.output, result)
    print(json.dumps({"verdict": result["verdict"], "sha256": digest}))
    raise SystemExit(0 if result["verdict"] == "PASS" else 2 if result["verdict"] == "BLOCKED" else 1)


if __name__ == "__main__":
    main()
