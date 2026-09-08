"""Durable, one-shot AS-014 formal population entrypoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.as014.publication import publish_json
from experiments.as014.qualification import HORIZON, execute
from tools.as014_evidence import publish


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    if manifest.get("schema") != "AS014_SEED_MANIFEST_V1":
        raise RuntimeError("AS014_FORMAL_SEED_MANIFEST_SCHEMA_INVALID")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--preflight-horizon", type=int)
    args = parser.parse_args()
    if args.work.exists():
        raise FileExistsError(f"AS014_FORMAL_WORK_EXISTS:{args.work}")
    manifest = _load_manifest(args.manifest)
    preflight_horizon = args.preflight_horizon
    if preflight_horizon is not None:
        if manifest.get("directive") != "AS014_FORMAL_RUNNER_PREFLIGHT":
            raise RuntimeError("AS014_FORMAL_HORIZON_OVERRIDE_FORBIDDEN")
        if not 1 <= preflight_horizon < HORIZON:
            raise ValueError("AS014_PREFLIGHT_HORIZON_INVALID")
    elif manifest.get("directive") != "UMBRA-AS-014":
        raise RuntimeError("AS014_FORMAL_MANIFEST_DIRECTIVE_INVALID")
    case_root = args.work / "case-results"

    def checkpoint_case(row: dict[str, Any]) -> None:
        path = case_root / f"{row['regime']}-{row['seed_index']:02d}-{row['seed']}.json"
        publish_json(path, row, schema="AS014_FORMAL_CASE_V1")

    result = execute(
        {
            "directive": "UMBRA-AS-014",
            "regimes": manifest["formal_regimes"],
        },
        args.work,
        on_case=checkpoint_case,
        horizon=preflight_horizon or HORIZON,
    )
    result["seed_manifest_path"] = str(args.manifest)
    result["case_result_count"] = len(list(case_root.glob("*.json")))
    result["all_case_results_durable"] = result["case_result_count"] == result["completed_runs"]
    computed = args.work / "AS014_FULL_POPULATION.computed-result.json"
    result["computed_result_sha256"] = publish_json(
        computed, result, schema="AS014_FORMAL_POPULATION_V1"
    )
    if result.get("all_completed") is True:
        final_name = (
            "AS014_FORMAL_RUNNER_PREFLIGHT.json"
            if preflight_horizon is not None
            else "AS014_FULL_POPULATION_RESULT.json"
        )
    else:
        final_name = "AS014_FULL_POPULATION_FAILURE.json"
    evidence_hash = publish(final_name, result)
    print(json.dumps({"terminal": result.get("terminal"), "sha256": evidence_hash}, sort_keys=True))
    if result.get("all_completed") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
