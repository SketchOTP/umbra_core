"""Publish the R6E-R1 final evidence manifest after all artifacts are present."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from tools.as003pr6er1_evidence import ROOT, publish


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    manifest_name = "AS003PR6ER1_FINAL_MANIFEST.json"
    artifacts = []
    for path in sorted(ROOT.iterdir()):
        if path.name == manifest_name:
            continue
        if path.is_file():
            artifacts.append({"name": path.name, "sha256": sha256(path), "bytes": path.stat().st_size})
    payload = {
        "schema": "AS003PR6ER1_FINAL_MANIFEST_V1",
        "verdict": "AS003PR6ER1_CANDIDATE_DERIVED_ROOT_CONTAMINATION_CONFIRMED",
        "repository_commit_at_manifest_creation": commit,
        "baseline": "e18d7c83a59988be4ed2cd5f9957820a7ab02968",
        "governance_start_commit": "30115d74f432d7091f458362aab781c558f2303f",
        "contract_lock_sha256": "8304fc56447a13ee7edbebcac9fa1066613d9dd1aaf903d5155634141c84515f",
        "r6d_matrix_sha256": "1a75f5de3fb59553d8b5a9d33ea3b2a553bacfe5ec37fbfd83a2c98ade649768",
        "historical_r6e_manifest_sha256": "9056418c728b71dd5778870c377cb619cede059c86551bfee74b21fc82b2fe00",
        "counts": {
            "r6d_rows": 1152,
            "candidate_derived_o0_rows": 512,
            "root_option_not_constructible_rows": 640,
            "lawful_common_root_rows": 0,
            "positive_relations": 0,
            "route_causal_relations": 0,
            "historical_r6e_route_causal_relations": 64,
            "organism_load_tick_control_shadow_r7": [0, 0, 0, 0, 0],
            "retries_reseeds": [0, 0],
        },
        "historical_artifacts_modified": False,
        "successor_started": False,
        "artifacts_excluding_manifest": artifacts,
        "artifact_count_excluding_manifest": len(artifacts),
    }
    digest = publish(manifest_name, payload)
    print(json.dumps({"manifest": manifest_name, "sha256": digest, "artifact_count": len(artifacts)}, sort_keys=True))


if __name__ == "__main__":
    main()
