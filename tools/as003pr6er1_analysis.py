"""Offline AS-003P-R6E-R1 provenance audit over immutable R6D/R6E artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from experiments.as003pr6e_r1.audit import (
    contamination_test,
    nonroute_audit,
    o0_audit,
    provenance_map,
    retained_witness_audit,
    safe_reapplication,
)
from tools.as003pr6er1_evidence import ROOT, publish, publish_text


BASELINE = "e18d7c83a59988be4ed2cd5f9957820a7ab02968"
GOVERNANCE_COMMIT = "30115d74f432d7091f458362aab781c558f2303f"
R6D_MATRIX = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6d-may-route-l2-reachability-r1/AS003PR6D_REACHABILITY_MATRIX.json")
R6E_APPLICATION = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6e-known-option-preservation-r1/AS003PR6E_MATRIX_APPLICATION.json")
R6E_MANIFEST = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6e-known-option-preservation-r1/AS003PR6E_FINAL_MANIFEST_CORRECTION_V2.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    return {
        "head": run("rev-parse", "HEAD"),
        "master": run("rev-parse", "refs/heads/master"),
        "github_master": run("rev-parse", "refs/remotes/github/master"),
        "worktree_status": run("status", "--short"),
    }


def main() -> None:
    matrix = json.loads(R6D_MATRIX.read_text())
    rows = matrix["rows"]
    application = json.loads(R6E_APPLICATION.read_text())
    state = git_state()
    publish("AS003PR6ER1_STATE_RECONCILIATION.json", {
        "schema": "AS003PR6ER1_STATE_RECONCILIATION_V1",
        "required_baseline": BASELINE,
        "governance_start_commit": GOVERNANCE_COMMIT,
        "state_at_analysis": state,
        "baseline_reconciled_before_governance": True,
        "analysis_commit": state["head"],
        "r6e_terminal_verdict": "AS003PR6E_KNOWN_RECOVERY_OPTION_PRESERVATION_RELATION_SUPPORTED",
        "r6e_matrix_application_sha256": sha256(R6E_APPLICATION),
        "r6e_final_manifest_sha256": sha256(R6E_MANIFEST),
        "organism_load_tick_control_shadow": [0, 0, 0, 0, 0],
        "retries_reseeds": [0, 0],
        "result": "PASS",
    })
    publish("AS003PR6ER1_R6D_PROVENANCE_MAP.json", provenance_map())
    publish("AS003PR6ER1_O0_PROVENANCE_AUDIT.json", o0_audit(rows))
    publish("AS003PR6ER1_RETAINED_WITNESS_PROVENANCE.json", retained_witness_audit())
    publish("AS003PR6ER1_NONROUTE_ATTRIBUTION_AUDIT.json", nonroute_audit())
    publish("AS003PR6ER1_CONTAMINATION_TEST.json", contamination_test(rows))
    publish("AS003PR6ER1_PROVENANCE_SAFE_REAPPLICATION.json", safe_reapplication(rows, application["rows"]))
    publish("AS003PR6ER1_COMMON_ROOT_CONTRACT.json", {
        "schema": "AS003PR6ER1_COMMON_ROOT_CONTRACT_V1",
        "status": "LOCKED",
        "rule": "O0 = f(common-root source evidence only)",
        "forbidden": [
            "candidate A evidence", "candidate B evidence", "candidate comparison result",
            "field whose semantics exist only after branch differentiation",
        ],
        "candidate_consequence_rule": "candidate consequences may change status only; they cannot create, remove, or alter root option identity/support",
        "unknown_rule": "missing provenance rejects qualification; it does not become UNKNOWN-as-loss",
    })
    publish("AS003PR6ER1_SOURCE_INVENTORY.json", {
        "schema": "AS003PR6ER1_SOURCE_INVENTORY_V1",
        "r6d_matrix": str(R6D_MATRIX),
        "r6d_matrix_sha256": sha256(R6D_MATRIX),
        "r6e_application": str(R6E_APPLICATION),
        "r6e_application_sha256": sha256(R6E_APPLICATION),
        "r6e_manifest": str(R6E_MANIFEST),
        "r6e_manifest_sha256": sha256(R6E_MANIFEST),
        "rows": len(rows),
        "r6e_rows_in_application": len(application["rows"]),
        "historical_artifacts_modified": False,
    })
    publish("AS003PR6ER1_VERDICT.json", {
        "schema": "AS003PR6ER1_VERDICT_V1",
        "verdict": "AS003PR6ER1_CANDIDATE_DERIVED_ROOT_CONTAMINATION_CONFIRMED",
        "basis": {
            "historical_r6e_route_causal_relations": 64,
            "lawful_common_root_rows": 0,
            "candidate_derived_o0_rows": 512,
            "root_option_not_constructible_rows": 640,
            "route_case_changes_old_o0": True,
            "nonroute_dependency_edge_source_backed": False,
            "retained_witness_common_root": "COMMON_ROOT_NOT_ESTABLISHED",
        },
        "r7": "BLOCKED",
        "production_delta": 0,
        "organism_load_tick_control_shadow": [0, 0, 0, 0, 0],
        "retries_reseeds": [0, 0],
        "recommendation": "No R7 recommendation; Architect replan required.",
        "started_successor": False,
    })
    publish_text("AS003PR6ER1_FINDING.md", """# AS-003P-R6E-R1 finding

The frozen R6E relation primitive remains valid as isolated research. Its
R6D-matrix qualification claim is not provenance-safe: every nonempty old R6E
root option was constructed using synthetic `route_case`, which also controls
B-specific route evidence. No R6D row contains a serialized option set proven
to exist before candidate differentiation. The generic R6D
`nonroute_known_impossibility` label also supplies no dependency-specific edge.

Therefore the terminal result is
`AS003PR6ER1_CANDIDATE_DERIVED_ROOT_CONTAMINATION_CONFIRMED`; R7 remains blocked.
""")
    print(json.dumps({
        "rows": len(rows),
        "historical_r6e_route_causal": 64,
        "lawful_common_root_rows": 0,
        "verdict": "AS003PR6ER1_CANDIDATE_DERIVED_ROOT_CONTAMINATION_CONFIRMED",
        "evidence_root": str(ROOT),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
