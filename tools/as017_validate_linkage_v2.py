"""Streaming semantic consumer for AS-017 recovery-linkage V2 exports."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Iterator

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.as017_evidence import (
    EvidenceFormatError,
    iter_jsonl,
    publish_json_once,
    stream_sha256,
    verify_trace_row_hash,
)
from tools.as017_review_v5_evidence import validate_linkage


SCHEMA = "AS017_RECOVERY_CERTIFICATE_LINKAGE_V2"


def _next(iterator: Iterator[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        return next(iterator)
    except StopIteration:
        return None


def validate_linkage_v2(
    summary_path: Path,
    records_path: Path,
    trace_path: Path,
    candidate_commit: str,
    *,
    expected_summary_sha256: str | None = None,
    expected_trace_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate V2 exports with bounded record memory and semantic checks."""
    failures: list[str] = []
    summary: dict[str, Any] = {}
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"verdict": "FAIL", "failures": [f"summary_read_failed:{type(exc).__name__}:{exc}"]}
    if summary.get("schema") != SCHEMA:
        failures.append("linkage_schema_mismatch")
    if summary.get("candidate_commit") != candidate_commit:
        failures.append("linkage_candidate_commit_mismatch")
    if expected_summary_sha256 is not None:
        try:
            if stream_sha256(summary_path) != expected_summary_sha256:
                failures.append("case_summary_hash_binding_mismatch")
        except OSError as exc:
            failures.append(f"summary_hash_failed:{type(exc).__name__}")
    try:
        observed_trace_sha256 = stream_sha256(trace_path)
        if expected_trace_sha256 is not None and observed_trace_sha256 != expected_trace_sha256:
            failures.append("trace_hash_binding_mismatch")
    except OSError as exc:
        observed_trace_sha256 = None
        failures.append(f"trace_hash_failed:{type(exc).__name__}")

    trace_rows = 0
    expected_linked = 0
    actual_linked = 0
    actual_unmatched = 0
    statuses: Counter[str] = Counter()
    semantic_failures: list[str] = []
    record_iterator: Iterator[dict[str, Any]] | None = None
    next_record: dict[str, Any] | None = None
    try:
        record_iterator = iter(iter_jsonl(records_path))
        next_record = _next(record_iterator)
        previous_trace_tick: int | None = None
        previous_record_tick: int | None = None
        for trace_row in iter_jsonl(trace_path):
            trace_rows += 1
            if not verify_trace_row_hash(trace_row):
                failures.append(f"trace_row_hash_mismatch:row_{trace_rows}")
            tick = trace_row.get("tick")
            if not isinstance(tick, int):
                failures.append(f"trace_tick_invalid:row_{trace_rows}")
                continue
            if previous_trace_tick is not None and tick <= previous_trace_tick:
                failures.append(f"trace_tick_not_strictly_increasing:row_{trace_rows}")
            previous_trace_tick = tick
            kernel = trace_row.get("viability_kernel")
            requires_link = isinstance(kernel, dict) and kernel.get("selected_recovery_certificate") is not None
            expected_linked += int(requires_link)
            if not isinstance(kernel, dict):
                statuses["NO_VIABILITY_OBLIGATION"] += 1
            elif not requires_link:
                statuses["ABSENT_CERTIFICATE"] += 1
            if next_record is not None:
                record_tick = next_record.get("tick")
                if not isinstance(record_tick, int):
                    failures.append(f"linkage_tick_invalid:record_{actual_linked + 1}")
                    next_record = _next(record_iterator)
                elif previous_record_tick is not None and record_tick <= previous_record_tick:
                    failures.append(f"linkage_tick_not_strictly_increasing:record_{actual_linked + 1}")
                if next_record is not None and isinstance(next_record.get("tick"), int):
                    if record_tick < tick:
                        failures.append(f"linkage_record_without_trace_row:tick_{record_tick}")
                        actual_unmatched += 1
                        previous_record_tick = record_tick
                        next_record = _next(record_iterator)
                    elif record_tick == tick:
                        actual_linked += 1
                        previous_record_tick = record_tick
                        trace_key = next_record.get("trace_row_hash")
                        if trace_key != trace_row.get("trace_row_hash"):
                            failures.append(f"link_{actual_linked - 1}:trace_row_binding_mismatch")
                        one_linkage = {
                            "schema": "AS017_RECOVERY_CERTIFICATE_LINKAGE_V1",
                            "candidate_commit": candidate_commit,
                            "trace_sha256": "",
                            "linked_records": [next_record],
                            "linked_count": 1,
                            "unmatched_count": 0,
                        }
                        one_summary, one_failures = validate_linkage(
                            one_linkage,
                            {str(trace_row.get("trace_row_hash")): trace_row},
                            "",
                            candidate_commit,
                        )
                        semantic_failures.extend(
                            f"link_{actual_linked - 1}:{failure}"
                            for failure in one_failures
                            if failure != "linkage_count_mismatch"
                        )
                        statuses.update(one_summary.get("continuation_status_counts", {}))
                        next_record = _next(record_iterator)
        while next_record is not None:
            actual_unmatched += 1
            failures.append(f"linkage_record_without_trace_row:tick_{next_record.get('tick')}")
            next_record = _next(record_iterator)
    except (OSError, EvidenceFormatError, json.JSONDecodeError) as exc:
        failures.append(f"stream_validation_failed:{type(exc).__name__}:{exc}")

    failures.extend(semantic_failures)
    if summary.get("trace_rows") != trace_rows:
        failures.append(f"trace_row_count_mismatch:expected_{summary.get('trace_rows')}_got_{trace_rows}")
    if summary.get("linked_records") != actual_linked:
        failures.append(f"linked_record_count_mismatch:expected_{summary.get('linked_records')}_got_{actual_linked}")
    if expected_linked != actual_linked:
        failures.append(f"linkage_capture_scope_mismatch:expected_{expected_linked}_got_{actual_linked}")
    if summary.get("unmatched_count") != actual_unmatched:
        failures.append(f"unmatched_count_mismatch:expected_{summary.get('unmatched_count')}_got_{actual_unmatched}")
    if summary.get("unmatched_count") != 0:
        failures.append("linkage_unmatched_records")
    if dict(sorted(summary.get("status_counts", {}).items())) != dict(sorted(statuses.items())):
        failures.append("continuation_status_counts_mismatch")
    try:
        if summary.get("records_sha256") != stream_sha256(records_path):
            failures.append("records_hash_mismatch")
    except OSError as exc:
        failures.append(f"records_hash_failed:{type(exc).__name__}")
    return {
        "schema": "AS017_RECOVERY_CERTIFICATE_LINKAGE_V2_VALIDATION_V1",
        "candidate_commit": candidate_commit,
        "summary_sha256": stream_sha256(summary_path) if summary_path.is_file() else None,
        "trace_sha256": observed_trace_sha256,
        "trace_rows": trace_rows,
        "linked_records": actual_linked,
        "unmatched_records": actual_unmatched,
        "continuation_status_counts": dict(sorted(statuses.items())),
        "semantic_failure_count": len(semantic_failures),
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--expected-summary-sha256")
    parser.add_argument("--expected-trace-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("AS017_V2_VALIDATION_OUTPUT_ALREADY_EXISTS")
    payload = validate_linkage_v2(
        args.summary,
        args.records,
        args.trace,
        args.candidate_commit,
        expected_summary_sha256=args.expected_summary_sha256,
        expected_trace_sha256=args.expected_trace_sha256,
    )
    digest = publish_json_once(args.output, payload)
    print(json.dumps({"verdict": payload["verdict"], "sha256": digest}, sort_keys=True))
    if payload["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
