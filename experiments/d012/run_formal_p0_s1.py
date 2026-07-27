"""Execute the single authorized UMBRA-D-012B2 Supplement S1 rerun."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from .failure_codes import SupervisionError
from .run_formal_p0 import P0Failure, run

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "evidence" / "d012"
SUPPLEMENT = EVIDENCE / "p0-supplement-s1.json"
REVIEW = EVIDENCE / "p0b2-independent-review.md"

ARTIFACTS = {
    "p0-formal-execution-manifest.json": "p0b2-formal-execution-manifest.json",
    "p0-process-trace.jsonl": "p0b2-process-trace.jsonl",
    "p0-schedule-trace.jsonl": "p0b2-schedule-trace.jsonl",
    "p0-resource-samples.jsonl": "p0b2-resource-samples.jsonl",
    "p0-worker-restart-results.json": "p0b2-worker-restart-results.json",
    "p0-checkpoint-results.json": "p0b2-checkpoint-results.json",
    "p0-snapshot-restart-results.json": "p0b2-snapshot-restart-results.json",
    "p0-chain-validation.json": "p0b2-chain-validation.json",
    "p0-raw-payload-audit.json": "p0b2-raw-payload-audit.json",
    "p0-process-audit.json": "p0b2-process-audit.json",
}


def execute(
    *, run_root: Path, execution_id: str, starting_commit: str
) -> dict[str, Any]:
    supplement = json.loads(SUPPLEMENT.read_text())
    if supplement.get("rerun_execution_identifier") != execution_id:
        raise SupervisionError("WORKER_MANIFEST_INVALID", "supplement_execution_id")
    if supplement.get("review_verdict") != "APPROVE" or "`APPROVE`" not in REVIEW.read_text():
        raise SupervisionError("WORKER_MANIFEST_INVALID", "review_not_approved")
    published = run_root / "published"
    trace_paths = {
        "formal_physiology_trace_path": str(
            run_root / "evidence" / "p0b2-physiology-trace.jsonl"
        ),
        "formal_recovery_trace_path": str(
            run_root / "evidence" / "p0b2-recovery-trace.jsonl"
        ),
        "formal_failure_path": str(run_root / "evidence" / "p0b2-first-failure.json"),
    }
    caught: BaseException | None = None
    result: dict[str, Any] = {}
    try:
        result = run(
            run_root=run_root,
            evidence_root=published,
            execution_id=execution_id,
            starting_commit=starting_commit,
            formal_trace_paths=trace_paths,
        )
    except (P0Failure, SupervisionError) as exc:
        caught = exc
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in ARTIFACTS.items():
        source = published / source_name
        if source.exists():
            shutil.copy2(source, EVIDENCE / target_name)
    for name in ("p0b2-physiology-trace.jsonl", "p0b2-recovery-trace.jsonl"):
        source = run_root / "evidence" / name
        if source.exists():
            shutil.copy2(source, EVIDENCE / name)
    result_path = published / "p0-run-result.json"
    if result_path.exists():
        result = json.loads(result_path.read_text())
    if caught is not None:
        raise caught
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--starting-commit", required=True)
    args = parser.parse_args()
    try:
        result = execute(
            run_root=args.run_root,
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
