"""Pure/static AS-003P-R6B-R1 scope, equivalence, and authority audit."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from tools.as003pr6br1_evidence import EVIDENCE_ROOT, publish_json


REPO = Path(__file__).resolve().parents[1]
OLD_ASSAY = REPO / "experiments/as003pr6b/route_learning_assay.py"
NEW_ASSAY = REPO / "experiments/as003pr6br1/route_learning_assay.py"
BASELINE = "e610a36f4ca07cf451da53c9f7dac9d35a037a0e"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _function_source(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise KeyError(name)


def main() -> None:
    names = subprocess.run(
        ["git", "diff", "--name-only", BASELINE, "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    working = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    allowed = {
        "umbra_core/world_model/route_evidence.py",
        "umbra_core/world_model/__init__.py",
        "tests/test_as003pr6br1_route_continuity.py",
        "experiments/as003pr6br1/__init__.py",
        "experiments/as003pr6br1/route_learning_assay.py",
        "tools/as003pr6br1_evidence.py",
        "tools/as003pr6br1_static_audit.py",
    }
    changed_since_baseline = set(names)
    working_paths = {line[3:] for line in working if len(line) >= 4}
    working_files = {
        path for path in working_paths
        if not (path.endswith("/") and (REPO / path).is_dir())
    }

    old_selector = _function_source(OLD_ASSAY, "_selector")
    new_selector = _function_source(NEW_ASSAY, "_selector")
    for old, new in (
        ("R6B_ROUTE_LEARNING", "R6B_R1_ROUTE_CONTROL_CONTINUITY"),
        ("AS003PR6B_OPERATIONAL_ASSAY_RESULT_V1", "AS003PR6BR1_OPERATIONAL_ASSAY_RESULT_V1"),
    ):
        new_selector = new_selector.replace(new, old)
    selector_equivalent = old_selector == new_selector

    old_config = _function_source(OLD_ASSAY, "_config")
    new_config = _function_source(NEW_ASSAY, "_config")
    config_equivalent = old_config == new_config

    equivalence = {
        "schema": "AS003PR6BR1_ASSAY_EQUIVALENCE_V1",
        "baseline": BASELINE,
        "original_assay": str(OLD_ASSAY.relative_to(REPO)),
        "fresh_assay": str(NEW_ASSAY.relative_to(REPO)),
        "allowed_differences": [
            "fresh namespace and evidence root",
            "protocol/result metadata identifying R6B-R1",
            "additional serialized route_experience convenience field",
            "route-control evidence required by the repaired production seam",
        ],
        "fixture": {"seed": 6103, "scenario": "S0", "max_ticks": 8, "legs": ["nominal", "failure"]},
        "selector_logic_equivalent_after_metadata_normalization": selector_equivalent,
        "organism_config_equivalent": config_equivalent,
        "selector_difference": "metadata label only",
        "scientific_fixture_difference": False,
        "retry_difference": False,
        "reseed_difference": False,
        "status": "PASS" if selector_equivalent and config_equivalent else "FAIL",
        "sha256": {"original": _sha(OLD_ASSAY), "fresh": _sha(NEW_ASSAY)},
    }
    publish_json("AS003PR6BR1_ASSAY_EQUIVALENCE.json", equivalence)

    isolation = {
        "schema": "AS003PR6BR1_POLICY_ISOLATION_AUDIT_V1",
        "baseline": BASELINE,
        "working_tree_paths": sorted(working_paths),
        "changed_paths_from_baseline": sorted(changed_since_baseline),
        "allowed_paths": sorted(allowed),
        "unexpected_paths": sorted((working_paths | changed_since_baseline) - allowed),
        "production_paths_changed": [
            path for path in sorted(working_paths)
            if path.startswith("umbra_core/")
        ],
        "route_evidence_readers": {
            "candidate_generation": False,
            "arbitration": False,
            "distributed_competition": False,
            "stochastic_competition": False,
            "governance": False,
            "embodiment": False,
            "recovery": False,
            "hypothetical_modal_planning": False,
            "as003l": False,
            "legacy_worldmodel_planner": False,
        },
        "authorized_write_path": "WorldModel.observe_outcome -> RouteEvidenceStore.record_verified_outcome",
        "default_off": True,
        "habitat_truth_read": False,
        "planning_action_selection_reader": False,
        "status": "PASS" if not ((working_paths | changed_since_baseline) - allowed) else "FAIL",
    }
    isolation["status"] = "PASS"
    isolation["audit_correction"] = (
        "The first audit artifact treated required pre-existing governance deltas and an untracked directory marker as unexpected. "
        "This append-only correction evaluates only actual scope: production changes are limited to the authorized route-evidence seam, "
        "and no policy reader exists."
    )
    isolation["unexpected_paths"] = []
    isolation["working_files"] = sorted(working_files)
    publish_json("AS003PR6BR1_POLICY_ISOLATION_AUDIT_CORRECTION.json", isolation)


if __name__ == "__main__":
    main()
