"""Run and validate the registered AS-018 excluded-development population."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from experiments.as014.qualification import HORIZON, REGIMES
from experiments.as018.development import execute
from experiments.d012.readonly_validation import validate_read_only


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()


def _validate_case(local_work: Path, row: dict[str, Any]) -> dict[str, Any]:
    database = local_work / f"{row['regime']}-{row['seed']}.sqlite"
    trace = local_work / str(row["decision_trace_filename"])
    result: dict[str, Any] = {
        "database": str(database),
        "database_sha256": _sha256(database),
        "identity": None,
        "target_ticks": int(row.get("target_ticks", HORIZON)),
        "ticks": int(row.get("ticks", 0)),
        "sqlite_integrity": None,
        "foreign_key_rows": None,
        "chain_status": None,
        "trace": str(trace),
        "trace_rows": 0,
        "envelope_evaluations": 0,
        "bounded_opportunities": 0,
        "reserve_activations": 0,
        "envelope_rejections": 0,
    }
    readonly = validate_read_only(database)
    with sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only=ON")
        foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    result.update(
        identity=readonly["identity"],
        sqlite_integrity=readonly["sqlite_integrity"],
        foreign_key_rows=len(foreign_keys),
        chain_status=readonly["chain_status"],
    )
    if not trace.exists():
        raise ValueError(f"missing_decision_trace:{trace}")
    with trace.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            result["trace_rows"] += 1
            kernel = record.get("viability_kernel")
            if not isinstance(kernel, dict):
                continue
            envelope = kernel.get("recovery_reachability_envelope")
            if not isinstance(envelope, dict):
                continue
            result["envelope_evaluations"] += len(envelope.get("decisions") or [])
            if envelope.get("activation"):
                result["reserve_activations"] += 1
            baseline = envelope.get("baseline") or {}
            if baseline.get("status") == "BOUNDED_RECOVERY_OPPORTUNITY":
                result["bounded_opportunities"] += 1
            result["envelope_rejections"] += len(envelope.get("rejected") or [])
    result["pass"] = bool(
        row.get("terminal") == "completed"
        and result["ticks"] == result["target_ticks"]
        and readonly["sqlite_integrity"] == "ok"
        and not foreign_keys
        and readonly["chain_status"] == "ok"
    )
    return result


def run(manifest_path: Path, output: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_hash = _sha256(manifest_path)
    output.mkdir(parents=True, exist_ok=False)
    work = output / "work"
    journal = output / "stage-journal.jsonl"
    validations: list[dict[str, Any]] = []

    def on_case(row: dict[str, Any]) -> None:
        validation = _validate_case(work, row)
        validations.append(validation)
        _append(journal, {
            "stage": "CASE_FINISHED" if validation["pass"] else "CASE_VALIDATION_FAILED",
            "regime": row["regime"],
            "seed": row["seed"],
            "candidate_commit": row.get("candidate_commit"),
            "validation": validation,
        })

    def on_start(start: dict[str, Any]) -> None:
        _append(journal, start)

    def on_execution_finished(row: dict[str, Any]) -> None:
        _append(journal, {
            "stage": "EXECUTION_FINISHED",
            "regime": row["regime"],
            "seed": row["seed"],
            "candidate_commit": row.get("candidate_commit"),
            "ticks": row.get("ticks"),
            "terminal": row.get("terminal"),
        })

    started = time.monotonic()
    result = execute(
        manifest,
        work,
        on_case=on_case,
        on_case_start=on_start,
        on_execution_finished=on_execution_finished,
        horizon=HORIZON,
    )
    result.update({
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_hash,
        "output_started_monotonic": started,
        "validation": validations,
        "validated_cases": sum(bool(item["pass"]) for item in validations),
        "validation_failures": [item for item in validations if not item["pass"]],
        "retries": 0,
        "reseeds": 0,
        "substitutions": 0,
        "formal_seeds_consumed": 0,
        "classification": "excluded_development_not_formal_qualification",
    })
    if result.get("all_completed") and result.get("validated_cases") != 32:
        result["all_completed"] = False
        result["terminal"] = "AS018_DEVELOPMENT_EVIDENCE_VALIDATION_FAIL"
    result_path = output / "result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["result_sha256"] = _sha256(result_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.manifest, args.output)
    print(json.dumps({
        "terminal": result.get("terminal"),
        "completed_runs": result.get("completed_runs"),
        "validated_cases": result.get("validated_cases"),
        "result_sha256": result.get("result_sha256"),
    }, sort_keys=True))
    return 0 if result.get("terminal") == "AS018_DEVELOPMENT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
