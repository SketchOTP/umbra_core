"""D-010 Stage A artifact loading, hashing, and validation (pre-freeze)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent

STAGE_A_ARTIFACTS: tuple[str, ...] = (
    "authoritative-event-allowlist.json",
    "observable-evidence-allowlist.json",
    "elapsed-contract-registry.json",
    "failure-code-registry.json",
    "temporal-event-schemas.json",
    "runtime-tick-classification.json",
)

PLACEHOLDER_MARKERS = ("PLACEHOLDER", "TODO_FREEZE", "0000000000000000")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict[str, Any]:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


def stage_a_paths() -> dict[str, Path]:
    return {name: EXP / name for name in STAGE_A_ARTIFACTS}


def compute_stage_a_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in STAGE_A_ARTIFACTS:
        path = EXP / name
        if path.is_file():
            out[f"experiments/d010/{name}"] = file_sha256(path)
    return out


def assert_no_placeholder_hashes(hashes: dict[str, str]) -> None:
    for key, value in hashes.items():
        blob = f"{key}:{value}"
        if any(marker in blob for marker in PLACEHOLDER_MARKERS):
            raise ValueError(f"placeholder_hash:{key}")
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"invalid_hash:{key}:{value}")


def write_stage_a_hashes(path: Path | None = None) -> dict[str, str]:
    hashes = compute_stage_a_hashes()
    assert_no_placeholder_hashes(hashes)
    payload = {
        "schema_version": "d010.stage-a-hashes.v1",
        "directive": "UMBRA-D-010",
        "frozen_before_execution": False,
        "artifacts": hashes,
        "bundle_hash": file_sha256_bytes(
            json.dumps(hashes, sort_keys=True).encode("utf-8")
        ),
    }
    target = path or (EXP / "stage-a-hashes.json")
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def file_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_seed_manifest(name: str) -> dict[str, Any]:
    return load_json(name)


def seed_set(manifest: dict[str, Any]) -> set[int]:
    seeds = manifest.get("seeds")
    if isinstance(seeds, list):
        return {int(s) for s in seeds}
    cells = manifest.get("cells", [])
    out: set[int] = set()
    for cell in cells:
        for seed in cell.get("paired_seeds", []):
            out.add(int(seed))
        if "seed" in cell:
            out.add(int(cell["seed"]))
    return out


def validate_seed_nonoverlap(
    development: dict[str, Any] | None = None,
    formal: dict[str, Any] | None = None,
) -> None:
    dev = development if development is not None else load_seed_manifest("development-seed-manifest.json")
    formal_m = formal if formal is not None else load_seed_manifest("formal-seed-manifest.json")
    dev_seeds = seed_set(dev)
    formal_seeds = seed_set(formal_m)
    overlap = dev_seeds & formal_seeds
    if overlap:
        raise ValueError(f"seed_overlap:{sorted(overlap)[:8]}")
    rule = dev.get("nonoverlap_rule") or formal_m.get("nonoverlap_rule")
    if rule:
        dev_ranges = rule.get("development_ranges", [])
        formal_ranges = rule.get("formal_ranges", [])
        for lo, hi in dev_ranges:
            for flo, fhi in formal_ranges:
                if max(int(lo), int(flo)) <= min(int(hi), int(fhi)):
                    raise ValueError(f"range_overlap:{lo}-{hi} vs {flo}-{fhi}")


def load_test_manifest() -> dict[str, Any]:
    return load_json("test-manifest.json")


def required_test_ids(manifest: dict[str, Any] | None = None) -> list[str]:
    man = manifest if manifest is not None else load_test_manifest()
    return [
        str(entry["test_id"])
        for entry in man.get("tests", [])
        if entry.get("required", True)
    ]


def collect_pytest_test_ids(test_file: Path | None = None) -> set[str]:
    path = test_file or (ROOT / "tests" / "test_d010.py")
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"^def (test_[a-zA-Z0-9_]+)\(", text, flags=re.MULTILINE))


def validate_test_manifest_complete(manifest: dict[str, Any] | None = None) -> list[str]:
    man = manifest if manifest is not None else load_test_manifest()
    errors: list[str] = []
    ids = [str(e.get("test_id", "")) for e in man.get("tests", [])]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_test_ids")
    present = collect_pytest_test_ids()
    required = set(required_test_ids(man))
    missing = required - present
    if missing:
        errors.extend(f"missing_test:{tid}" for tid in sorted(missing))
    gate13 = [
        e
        for e in man.get("tests", [])
        if int(e.get("gate", -1)) == 13 and e.get("required", True)
    ]
    if not gate13:
        errors.append("no_required_gate13_tests")
    for entry in gate13:
        if "skip" in str(entry.get("expected_execution_mode", "")).lower():
            errors.append(f"gate13_skip_placeholder:{entry.get('test_id')}")
    return errors
