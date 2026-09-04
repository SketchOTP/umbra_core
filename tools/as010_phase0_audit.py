"""AS-010 zero-organism configuration and inheritance audit."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from experiments.as010.full_config import as010_config, semantic_fingerprint
from experiments.d014.run_formal import config as d014_config
from experiments.as007.qualification import as007_config

BASELINE = "b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b"
FREEZE = "f0ac33212b3cb0081e16341bba31db69043a9292"
ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    db = Path("/tmp/as010-config-audit.sqlite")
    reduced = d014_config(1, db, "R0")
    full = as007_config(1, db, "R0", Path("/tmp/decision.jsonl"), Path("/tmp/planning.jsonl"))
    canonical = as010_config(1, db, "R0")
    fp_reduced, fp_full, fp_canonical = map(semantic_fingerprint, (reduced, full, canonical))
    relevant = {}
    for key in sorted(set(fp_reduced) | set(fp_full) | set(fp_canonical)):
        relevant[key] = {"D014": fp_reduced.get(key), "AS007": fp_full.get(key), "AS010": fp_canonical.get(key), "classification": "MATCH" if fp_full.get(key) == fp_canonical.get(key) else "SEMANTIC_MISMATCH"}
    lineage = {
        "schema": "AS010_CONFIGURATION_LINEAGE_AUDIT_V1", "directive": "UMBRA-AS-010", "baseline": BASELINE,
        "fields": relevant,
        "material_mismatch_from_reduced": {"bounded_continuation_enabled": [False, True], "world_model_config.route_demand_learning_enabled": [False, True]},
        "classification": "AS007_FULL_CONFIGURATION_IS_NOT_D014_REDUCED_CONFIGURATION",
        "organism_creation": 0, "organism_ticks": 0,
    }
    equivalence = {"schema": "AS010_AS007_RUNTIME_CONFIG_EQUIVALENCE_V1", "directive": "UMBRA-AS-010", "baseline": BASELINE, "comparison": relevant, "verdict": "AS007_FULL_CONFIGURATION_REPRODUCED" if all(item["classification"] == "MATCH" for item in relevant.values()) else "SEMANTIC_MISMATCH", "organism_creation": 0, "organism_ticks": 0}
    diff = subprocess.run(["git", "diff", "--name-only", FREEZE, "HEAD", "--", "umbra_core"], check=True, capture_output=True, text=True).stdout.splitlines()
    inheritance = {"schema": "AS010_PRODUCTION_INHERITANCE_PROOF_V1", "directive": "UMBRA-AS-010", "as007_freeze": FREEZE, "current_baseline": BASELINE, "production_files_changed_since_freeze": diff, "production_semantic_delta": 0 if not diff else len(diff), "verdict": "PASS" if not diff else "AS010_PRODUCTION_INHERITANCE_FAIL"}
    contract = {"schema": "AS010_FULL_CONFIGURATION_CONTRACT_V1", "directive": "UMBRA-AS-010", "baseline": BASELINE, "source": "AS-007 scientific configuration plus current AS-009 HabitatEngine authority", "required": {"bounded_continuation_enabled": True, "world_model_enabled": True, "world_model_config.route_demand_learning_enabled": True, "world_model_config.planning_enabled": True, "habitat_enabled": True, "temporal_enabled": True, "embodiment_adapter_enabled": True}, "authority": "terminal readiness remains production-defined; planning remains non-authoritative", "organism_creation": 0, "organism_ticks": 0}
    write(ROOT / "AS010_CONFIGURATION_LINEAGE_AUDIT.json", lineage)
    write(ROOT / "AS010_AS007_RUNTIME_CONFIG_EQUIVALENCE.json", equivalence)
    write(ROOT / "AS010_PRODUCTION_INHERITANCE_PROOF.json", inheritance)
    write(ROOT / "AS010_FULL_CONFIGURATION_CONTRACT.json", contract)
    print(json.dumps({"lineage": lineage, "equivalence": equivalence, "inheritance": inheritance}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
