"""Durable one-shot AS-015 formal-population CLI."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from experiments.as014.publication import publish_json
from experiments.as015.qualification import HORIZON, execute
from tools.as015_evidence import publish


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    if manifest.get("schema") != "AS015_SEED_MANIFEST_V1":
        raise RuntimeError("AS015_FORMAL_SEED_MANIFEST_SCHEMA_INVALID")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--preflight-horizon", type=int)
    parser.add_argument("--preflight-label")
    args = parser.parse_args()
    if args.work.exists():
        raise FileExistsError(f"AS015_FORMAL_WORK_EXISTS:{args.work}")
    manifest = _load_manifest(args.manifest)
    if args.preflight_horizon is not None:
        if manifest.get("directive") != "AS015_FORMAL_RUNNER_PREFLIGHT":
            raise RuntimeError("AS015_FORMAL_HORIZON_OVERRIDE_FORBIDDEN")
        if not 1 <= args.preflight_horizon < HORIZON:
            raise ValueError("AS015_PREFLIGHT_HORIZON_INVALID")
        if args.preflight_label is None:
            raise ValueError("AS015_PREFLIGHT_LABEL_REQUIRED")
        if not re.fullmatch(r"[A-Z0-9_]{1,64}", args.preflight_label):
            raise ValueError("AS015_PREFLIGHT_LABEL_INVALID")
    elif args.preflight_label is not None:
        raise ValueError("AS015_FORMAL_PREFLIGHT_LABEL_FORBIDDEN")
    elif manifest.get("directive") != "UMBRA-AS-015":
        raise RuntimeError("AS015_FORMAL_MANIFEST_DIRECTIVE_INVALID")

    case_root = args.work / "case-results"

    def checkpoint_case(row: dict[str, Any]) -> None:
        publish_json(case_root / f"{row['regime']}-{row['seed_index']:02d}-{row['seed']}.json", row, schema="AS015_FORMAL_CASE_V1")

    result = execute(
        {"directive": "UMBRA-AS-015", "formal_regimes": manifest["formal_regimes"]},
        args.work,
        on_case=checkpoint_case,
        horizon=args.preflight_horizon or HORIZON,
        preflight=args.preflight_horizon is not None,
    )
    result["seed_manifest_path"] = str(args.manifest)
    result["case_result_count"] = len(list(case_root.glob("*.json")))
    result["all_case_results_durable"] = result["case_result_count"] == result["completed_runs"]
    computed = args.work / "AS015_FULL_POPULATION.computed-result.json"
    result["computed_result_sha256"] = publish_json(computed, result, schema="AS015_FORMAL_POPULATION_V1")
    if args.preflight_horizon is not None:
        suffix = "RESULT" if result.get("all_completed") else "FAILURE"
        name = f"AS015_PREFLIGHT_{args.preflight_label}_{suffix}.json"
    else:
        name = (
            "AS015_FULL_POPULATION_RESULT.json"
            if result.get("all_completed")
            else "AS015_FULL_POPULATION_FAILURE.json"
        )
    evidence_hash = publish(name, result)
    print(json.dumps({"terminal": result.get("terminal"), "sha256": evidence_hash}, sort_keys=True))
    if result.get("all_completed") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
