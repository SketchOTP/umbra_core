"""Durable AS-016 population runner with a separate non-formal CLI mode."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from experiments.as014.publication import publish_json
from experiments.as016.qualification import HORIZON, execute
from tools.as016_evidence import publish


FORMAL_DIRECTIVE = "UMBRA-AS-016"
PREFLIGHT_DIRECTIVE = "AS016_FORMAL_RUNNER_PREFLIGHT"


def _manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if value.get("schema") != "AS016_SEED_MANIFEST_V1":
        raise RuntimeError("AS016_FORMAL_SEED_MANIFEST_SCHEMA_INVALID")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--preflight-horizon", type=int)
    parser.add_argument("--preflight-label")
    args = parser.parse_args()
    if args.work.exists():
        raise FileExistsError(f"AS016_FORMAL_WORK_EXISTS:{args.work}")
    manifest = _manifest(args.manifest)
    is_preflight = args.preflight_horizon is not None
    if is_preflight:
        if manifest.get("directive") != PREFLIGHT_DIRECTIVE:
            raise RuntimeError("AS016_FORMAL_HORIZON_OVERRIDE_FORBIDDEN")
        if not 1 <= args.preflight_horizon < HORIZON:
            raise ValueError("AS016_PREFLIGHT_HORIZON_INVALID")
        if args.preflight_label is None or not re.fullmatch(r"[A-Z0-9_]{1,64}", args.preflight_label):
            raise ValueError("AS016_PREFLIGHT_LABEL_INVALID")
    elif args.preflight_label is not None or manifest.get("directive") != FORMAL_DIRECTIVE:
        raise RuntimeError("AS016_FORMAL_MANIFEST_DIRECTIVE_INVALID")

    case_root = args.work / "case-results"

    def checkpoint_case(row: dict[str, Any]) -> None:
        publish_json(
            case_root / f"{row['regime']}-{row['seed_index']:02d}-{row['seed']}.json",
            row,
            schema="AS016_FORMAL_CASE_V1",
        )

    result = execute(
        {"directive": FORMAL_DIRECTIVE, "formal_regimes": manifest["formal_regimes"]},
        args.work,
        on_case=checkpoint_case,
        horizon=args.preflight_horizon or HORIZON,
        preflight=is_preflight,
    )
    result.update(
        seed_manifest_path=str(args.manifest),
        case_result_count=len(list(case_root.glob("*.json"))),
    )
    result["all_case_results_durable"] = result["case_result_count"] == result["completed_runs"]
    computed = args.work / "AS016_FULL_POPULATION.computed-result.json"
    result["computed_result_sha256"] = publish_json(
        computed, result, schema="AS016_FORMAL_POPULATION_V1"
    )
    if is_preflight:
        suffix = "RESULT" if result.get("all_completed") else "FAILURE"
        name = f"AS016_PREFLIGHT_{args.preflight_label}_{suffix}.json"
    else:
        name = "AS016_FORMAL_POPULATION_RESULT_V1.json" if result.get("all_completed") else "AS016_FORMAL_POPULATION_FAILURE_V1.json"
    digest = publish(name, result)
    print(json.dumps({"terminal": result.get("terminal"), "sha256": digest}, sort_keys=True))
    if result.get("all_completed") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
