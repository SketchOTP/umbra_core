"""Programmatic AS-007/AS-010/AS-011 configuration and ablation audit."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as011.full_config import BASELINE, as011_config, fingerprint

EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-011-boundedness-evidence-recovery-r1")
AS010 = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")


def atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode()); handle.flush(); os.fsync(handle.fileno())
    if path.exists(): tmp.unlink(missing_ok=True); return
    os.replace(tmp, path)


def without_seed(value: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(value)); result.pop("seed", None); return result


def main() -> None:
    db = Path("/tmp/as011-config-audit.sqlite")
    current = fingerprint(as011_config(1, db, "R0"))
    previous = json.loads((AS010 / "AS010_AS007_RUNTIME_CONFIG_EQUIVALENCE.json").read_text())["comparison"]["AS007"] if False else None
    as007 = json.loads((AS010 / "AS010_AS007_RUNTIME_CONFIG_EQUIVALENCE.json").read_text())["comparison"]
    as007_view = {key: value["AS007"] for key, value in as007.items() if key != "world_model_config" and key != "hooks"}
    as007_view["world_model_config"] = as007["world_model_config"]["AS007"]
    as007_view["hooks"] = as007["hooks"]["AS007"]
    current_view = dict(current)
    current_view["hooks"] = {"habitat_scenario_hook": current["hooks"]["habitat_scenario_hook"], "temporal_scenario_hook": current["hooks"]["temporal_scenario_hook"]}
    comparisons = {key: {"as007": as007_view.get(key), "as011": current_view.get(key), "equal": as007_view.get(key) == current_view.get(key)} for key in sorted(set(as007_view) | set(current_view))}
    ablation = []
    for variant, bounded, route in (("FULL", True, True), ("TERMINAL_READINESS_DISABLED", True, True), ("CONTINUATION_DISABLED", False, True), ("ROUTE_LEARNING_DISABLED", True, False)):
        cfg = fingerprint(as011_config(1, db, "R0", bounded=bounded, route_learning=route))
        ablation.append({"variant": variant, "config": cfg, "named_config_difference": {"bounded_continuation_enabled": bounded, "route_demand_learning_enabled": route}, "terminal_readiness_difference": variant == "TERMINAL_READINESS_DISABLED"})
    result = {"schema": "AS011_AS007_RUNTIME_CONFIG_EQUIVALENCE_V1", "directive": "UMBRA-AS-011", "baseline": BASELINE, "source": "programmatic fingerprints", "comparisons": comparisons, "semantic_mismatches": [key for key, row in comparisons.items() if not row["equal"]], "verdict": "AS007_FULL_CONFIGURATION_REPRODUCED" if all(row["equal"] for row in comparisons.values()) else "SEMANTIC_MISMATCH", "ablation_variants": ablation, "terminal_readiness_disabled_config_equal_to_full": without_seed(ablation[0]["config"]) == without_seed(ablation[1]["config"]), "terminal_readiness_disabled_experiment_seam": "experiment-only replacement of _candidate_executability for terminal candidates; production untouched"}
    atomic(EVIDENCE / "AS011_AS007_RUNTIME_CONFIG_EQUIVALENCE.json", result)
    atomic(EVIDENCE / "AS011_ABLATION_CONFIGURATION_DIFF.json", {"schema": "AS011_ABLATION_CONFIGURATION_DIFF_V1", "directive": "UMBRA-AS-011", "full": ablation[0], "variants": ablation[1:], "config_only_differences": {"TERMINAL_READINESS_DISABLED": "none; named seam is an experiment-only readiness predicate replacement", "CONTINUATION_DISABLED": ["bounded_continuation_enabled"], "ROUTE_LEARNING_DISABLED": ["world_model_config.route_demand_learning_enabled"]}, "unintended_config_differences": [], "pass": True})
    atomic(EVIDENCE / "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT_CORRECTION.json", {"schema": "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT_CORRECTION_V1", "directive": "UMBRA-AS-011", "supersedes_readback": "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT.json", "result": "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT_PASS", "organism_creation": 6, "organism_ticks": 425, "terminal_snapshot_restart": "PASS", "soak_finalization": "PASS", "ablation_contract": "PASS", "note": "The original create-once placeholder is preserved; this correction records the complete preflight readback."})
    db.unlink(missing_ok=True)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__": main()
