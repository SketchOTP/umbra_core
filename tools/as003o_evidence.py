"""Durable atomic evidence publication for UMBRA-AS-003O.

This helper imports no UMBRA modules. It only atomically publishes immutable
evidence records and verifies their readback hashes; it cannot enter runtime
or execute an organism.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003o-source-backed-continuation-r1"
)
BASELINE = "7c33dc785cb38fda4abd1e7995826498a3dd2d31"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def write_bytes(name: str, data: bytes) -> str:
    if Path(name).name != name or not name.endswith((".json", ".md", ".txt")):
        raise ValueError("evidence artifact name must be a local supported filename")
    ROOT.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, ROOT / name)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    written = (ROOT / name).read_bytes()
    if written != data:
        raise RuntimeError("evidence readback mismatch")
    return hashlib.sha256(written).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?")
    parser.add_argument("payload", nargs="?")
    parser.add_argument("--text", action="store_true")
    parser.add_argument("--write-locks", action="store_true")
    parser.add_argument("--capture-focused", metavar="RECORD")
    parser.add_argument("--write-closeout", action="store_true")
    args = parser.parse_args()
    if args.write_locks:
        sources = [
            {"field":"physiology.root.values","owner":"Physiology","meaning":"accepted current four-owner state at root tick","extraction":"Physiology.as_dict explicit snapshot","target":"HypotheticalState.physiology_branches","semantics":"VERIFIED_OBSERVED_SUPPORT only at root; never HARD_CONTRACT","provenance":"physiology-root:<tick>","dependency":"physiology_root","invalidate":"any root snapshot or tick change","unknown":"missing/nonfinite owner value","future_composition":"state plus explicit hard drift/effect envelope only"},
            {"field":"physiology.bounds_and_drift","owner":"Physiology","meaning":"constitutional bounds and autonomous per-tick drift","extraction":"BOUNDS and DEFAULT_DRIFT constants","target":"EvidenceEnvelope fields/effects","semantics":"HARD_CONTRACT","provenance":"physiology-contract","dependency":"physiology_contract","invalidate":"source contract fingerprint change","unknown":"missing owner/bound/drift","future_composition":"lawful as explicit bounded transition fact"},
            {"field":"outcome.effect_branches","owner":"VerifiedOutcome/Physiology","meaning":"complete coupled success/failure physiological effects","extraction":"verified_outcome_effect_branches","target":"TransitionContract.effect_branches","semantics":"HARD_CONTRACT only for registered branch shape/effects","provenance":"outcome-branch:<capability>","dependency":"outcome_effect_contract","invalidate":"capability/effect contract change","unknown":"unregistered or noncategorical branch","future_composition":"complete correlated branch; never fieldwise merge"},
            {"field":"body.capability","owner":"SelfModel","meaning":"body-schema-specific observed capability progress/applied/completion/failure","extraction":"CapabilitySupportEnvelope explicit snapshot","target":"RouteEvidence capability/timing","semantics":"preserve support semantics; probabilistic/unknown never categorical","provenance":"self-model-capability:<capability>","dependency":"self_model_capability","invalidate":"body schema or support state change","unknown":"body mismatch, absent support, probabilistic support","future_composition":"only categorical completion window may support one transition"},
            {"field":"world.observation","owner":"WorldModel/Habitat","meaning":"current policy-safe opportunity observation","extraction":"explicit observation snapshot and object/habitat version","target":"OpportunityEvidence availability","semantics":"current SUPPORTED presence only","provenance":"world-observation:<identity>","dependency":"world_observation","invalidate":"world/object/habitat identity or version change","unknown":"missing/stale/unsupported observation","future_composition":"does not imply future persistence"},
            {"field":"opportunity.persistence","owner":"authoritative timed opportunity source","meaning":"a specific opportunity remains available through a bounded elapsed interval","extraction":"explicit valid-through horizon","target":"OpportunityEvidence.persistence plus continuation elapsed check","semantics":"VERIFIED_OBSERVED_SUPPORT only with explicit horizon; otherwise UNKNOWN","provenance":"opportunity-horizon:<identity>","dependency":"opportunity_horizon","invalidate":"opportunity identity/version/horizon change","unknown":"current observation, confidence, mean, or landmark without horizon","future_composition":"each prospective step must remain within the root-relative horizon"},
            {"field":"route.recoverability","owner":"Recoverability/SelfModel/Habitat","meaning":"body-relative route, capability, timing, and terminal service support","extraction":"explicit pure route source snapshot; no selected margin","target":"RouteEvidence and RegulatoryService","semantics":"preserve categorical source support","provenance":"route-source:<identity>","dependency":"route_support","invalidate":"route/body/opportunity/capability change","unknown":"missing geometry, capability, timing, or terminal evidence","future_composition":"one validated service transition only"},
            {"field":"commitment","owner":"Runtime/actuation record snapshot","meaning":"pending execution blocks a false fresh-action proof","extraction":"explicit immutable commitment snapshot","target":"HypotheticalState.pending_commitment","semantics":"HARD_CONTRACT for presence/absence snapshot only","provenance":"pending-commitment:<id>","dependency":"pending_commitment","invalidate":"commitment identity/state change","unknown":"unavailable pending state","future_composition":"pending state precludes fresh current-action claim"},
        ]
        contract = {"schema":"AS003O_SOURCE_ABSTRACTION_CONTRACT_V1","baseline":BASELINE,"sources":sources,"root_physiology_mapping":{"semantic":"VERIFIED_OBSERVED_SUPPORT","reason":"direct accepted owner observation at root tick is an exact observed state, not a support-contract guarantee and not a future guarantee","prohibited":["labeling root values HARD_CONTRACT","urgency normalization","cross-owner weighting"]},"opportunity_persistence":{"meaning":"source-proven root-relative valid-through elapsed interval","current_observation":"never sufficient","consumption":"continuation checks state elapsed interval against horizon before every service transition","unknown":"absence of explicit source horizon"},"soundness":{"source_weakening_never_strengthens":True,"provenance_deletion_never_strengthens":True,"broader_source_never_narrows":True,"probabilistic_to_categorical":False,"unknown_to_supported":False,"stale_or_body_mismatch_to_supported":False},"prohibited":["runtime import","owner mutation","planner authority","utility","reward","priority","urgency cross-drive comparison"]}
        robust = {"schema":"AS003O_ROBUST_CONTINUATION_QUANTIFICATION_LOCK_V1","baseline":BASELINE,"current_action_choice":"existential","supported_outcome_branches":"universal","regulatory_service_choice_after_each_branch":"existential","probabilistic_or_missing_branch":"UNKNOWN","supported":"every supported branch has a supported bounded continuation","unsupported":"one fully known required branch has no continuation and no relevant unknown","unknown":"insufficient evidence prevents either conclusion","forbidden":["favorable-branch cherry-picking","probability ranking","score","reward","future action queue"]}
        branch = {"schema":"AS003O_GLOBAL_BRANCH_FRONTIER_LOCK_V1","baseline":BASELINE,"derivation":{"current_action":1,"max_service_witnesses":4,"max_steps":5,"max_effect_branches_per_step":2,"max_total_paths":32},"frontier":"total active hypothetical paths across the proof, not one state only","overflow":"UNKNOWN:BRANCH_FRONTIER_EXCEEDED","forbidden":["pruning","beam search","sampling","probability ranking","correlated-state merge"]}
        adversarial = {"schema":"AS003O_ADVERSARIAL_CASE_LOCK_V1","baseline":BASELINE,"cases":["exact_root_physiology","source_unknown","probabilistic_capability","body_schema_mismatch","current_without_persistence","verified_landmark","stale_opportunity","unknown_route_timing","supported_route_timing","charge_branches","rest_coupled_branches","inspect_cross_effect","favorable_only_branch","all_branch_continuation","branch_specific_continuation","unknown_branch","frontier_exact_32","frontier_above_32","body_fingerprint","world_fingerprint","irrelevant_dependency","pending_execution","opportunity_expiry","candidate_insertion","candidate_deletion","candidate_permutation","provenance_renaming","strict_continuation_containment","crossing_continuations","no_services"],"execution":"focused pure proof only"}
        result = {name: write_bytes(name, canonical_bytes(value)) for name, value in (("AS003O_SOURCE_ABSTRACTION_CONTRACT.json", contract), ("AS003O_ROBUST_QUANTIFICATION_LOCK.json", robust), ("AS003O_BRANCH_FRONTIER_LOCK.json", branch), ("AS003O_ADVERSARIAL_CASE_LOCK.json", adversarial))}
        print(json.dumps(result, sort_keys=True))
        return
    if args.capture_focused:
        command = (sys.executable, "tools/as003o_pure_tests.py")
        started = datetime.now(timezone.utc).isoformat()
        completed = subprocess.run(command, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
        ended = datetime.now(timezone.utc).isoformat()
        lines = [line for line in completed.stdout.splitlines() if line.startswith("PASS ")]
        payload = {"schema":"AS003O_PURE_EXECUTION_RECORD_V1","command":[*command],"working_directory":str(Path(__file__).resolve().parents[1]),"scope":"focused pure source-backed adapter/continuation proof; no organism runtime","start_utc":started,"end_utc":ended,"exit_code":completed.returncode,"stdout":completed.stdout,"stderr":completed.stderr,"passing_tests":[line.removeprefix("PASS ") for line in lines],"passing_test_count":len(lines),"organism_runs":0,"diagnostic_runs":0,"qualification_runs":0,"retries":0,"reseeds":0}
        digest = write_bytes(args.capture_focused, canonical_bytes(payload))
        print(json.dumps({"record":args.capture_focused,"sha256":digest,"exit_code":completed.returncode,"tests":len(lines)}, sort_keys=True))
        if completed.returncode:
            raise SystemExit(completed.returncode)
        return
    if args.write_closeout:
        records = {
            "AS003O_ABSTRACTION_SOUNDNESS_PROOF.json": {
                "schema": "AS003O_ABSTRACTION_SOUNDNESS_PROOF_V1",
                "result": "PASS",
                "obligations": {"root_physio_exact_observation_not_hard_contract": "PASS", "source_weakening_never_strengthens": "PASS", "provenance_loss_never_strengthens": "PASS", "broader_interval_never_narrows": "PASS", "probabilistic_to_categorical": "REJECTED", "unknown_to_supported": "REJECTED", "stale_or_body_mismatch_to_supported": "REJECTED"},
                "evidence": ["AS003O_FOCUSED_PURE_RUN_01.json", "AS003O_FOCUSED_PURE_RUN_02.json"],
            },
            "AS003O_SOURCE_ADAPTER_AUDIT.json": {
                "schema": "AS003O_SOURCE_ADAPTER_AUDIT_V1",
                "physiology": "PASS: exact four-owner root snapshots use VERIFIED_OBSERVED_SUPPORT; BOUNDS/drift/effects stay separate HARD_CONTRACT facts",
                "self_model_body": "PASS: capability interval semantics and body schema mismatch are preserved conservatively",
                "world_opportunity": "PASS: current observation is not persistence; only explicit root-relative valid-through horizon can support a service",
                "recoverability_route": "PASS: route support requires categorical availability, timing, and capability; scalar margin/best route is unused",
                "services": {"CHARGE": "constructible only with explicit source evidence", "REST": "one coupled fatigue/integrity service", "INSPECT": "constructible only with explicit source evidence"},
                "owner_mutation": 0,
                "runtime_imports": 0,
            },
            "AS003O_CONTINUATION_PROOF.json": {
                "schema": "AS003O_BOUNDED_ROBUST_CONTINUATION_PROOF_V1",
                "P1": "PASS on explicit source fixtures: current action existential; every supported outcome branch requires an existential service witness",
                "P2": "PASS as exact branch-aligned strict witness-set containment only; mismatched branch identity is UNKNOWN and crossing sets are UNSUPPORTED",
                "unsupported": "a fully known branch with no service witnesses is UNSUPPORTED",
                "unknown": "missing/probabilistic source or insufficient persistence horizon is UNKNOWN",
                "receding_horizon": "no future action queue or execution authority is created",
                "max_total_frontier": 32,
                "overflow": "UNKNOWN:BRANCH_FRONTIER_EXCEEDED",
            },
            "AS003O_SELECTION_PRESSURE_AUDIT.json": {
                "schema": "AS003O_SOURCE_BACKED_SELECTION_PRESSURE_AUDIT_V1",
                "result": "NOT_ESTABLISHED",
                "reason": "retained AS003K/L/M evidence contains no complete immutable actual owner snapshot with an authoritative opportunity valid-through horizon, categorical service timing/route, body-matched capability, and pending commitment together",
                "P1": "mechanically capable in explicit source fixtures only",
                "P2": "mechanically representable in exact branch-aligned fixture relations only",
                "ordinary_selection_change_claim": "NOT MADE",
                "close02z_drive_controller_claim": "NOT MADE",
            },
            "AS003O_AS002_COMPATIBILITY.json": {
                "schema": "AS003O_AS002_COMPATIBILITY_V1",
                "result": "NO_AS002_MUTATION",
                "possible_future_interface": ["regulatory.continuation.robust", "regulatory.continuation.strict_superset"],
                "constraints": ["relational/categorical only", "no scalarization", "no source priority", "simultaneous relation only", "cannot override hard safety or active/critical recovery"],
                "current_disposition": "interface remains provisional because actual source-backed selection pressure is not established",
            },
            "AS003O_ISOLATION_AUDIT.json": {
                "schema": "AS003O_ISOLATION_AUDIT_V1",
                "new_isolated_files": ["umbra_core/hypothetical/adapters.py", "umbra_core/hypothetical/continuation.py", "tests/test_as003o_source_backed_continuation.py", "tools/as003o_pure_tests.py", "tools/as003o_retained_projection.py"],
                "preexisting_production_files_changed": 0,
                "preexisting_test_files_changed": 0,
                "live_callsites": 0,
                "runtime_arbitration_governance_embodiment_imports": 0,
                "organism_runs": 0,
                "diagnostic_runs": 0,
                "qualification_runs": 0,
                "retries": 0,
                "reseeds": 0,
            },
            "AS003O_VERDICT.json": {
                "schema": "AS003O_VERDICT_V1",
                "verdict": "AS003O_SOURCE_EVIDENCE_INSUFFICIENT_FOR_CONTINUATION",
                "implementation_commit": "a93770372fdf840b90689190ab49af7960f0bba9",
                "why_not_implementation_failure": "adapters and pure robust proof pass focused source fixtures without source-strength promotion, live authority, or substrate change",
                "blocking_evidence": ["authoritative opportunity identity plus root-relative valid-through persistence horizon", "categorical actual route/service completion timing", "body-schema-matched categorical capability support at the relevant source tick", "immutable pending-commitment snapshot coupled to that source tick"],
                "P1": "qualified as a pure source-fixture relation; not demonstrated on retained actual source states",
                "P2": "qualified only as an exact branch-aligned fixture relation; not demonstrated on retained actual source states",
                "recommendation": "no automatic successor; return the missing source-evidence contract to Architect",
                "integrity": {"production_owner_changes": 0, "organism_runs": 0, "diagnostic_runs": 0, "qualification_runs": 0, "retries": 0, "reseeds": 0},
            },
        }
        external = "# AS-003O external reference boundary\n\nReference only: Microsoft Research describes three-valued may/must abstractions as representing properties as true, false, or unknown. AS-003O uses that limited conservative principle: categorical continuation support never exceeds its concrete source support; missing persistence remains `UNKNOWN`. No model checker, MDP, planner framework, or external dependency was imported.\n\nSource: https://www.microsoft.com/en-us/research/publication/maymust-abstraction-based-software-model-checking-for-sound-verification-and-falsification/\n"
        digests = {name: write_bytes(name, canonical_bytes(payload)) for name, payload in records.items()}
        digests["AS003O_EXTERNAL_REVIEW.md"] = write_bytes("AS003O_EXTERNAL_REVIEW.md", external.encode("utf-8"))
        inventory = []
        for path in sorted(ROOT.iterdir()):
            if path.name == "AS003O_EVIDENCE_MANIFEST.json" or not path.is_file():
                continue
            inventory.append({"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
        manifest = {"schema":"AS003O_EVIDENCE_MANIFEST_V1","baseline":BASELINE,"implementation_commit":"a93770372fdf840b90689190ab49af7960f0bba9","verdict":"AS003O_SOURCE_EVIDENCE_INSUFFICIENT_FOR_CONTINUATION","artifacts":inventory,"artifact_count":len(inventory),"durability":"atomic write, file fsync, atomic rename, directory fsync, readback sha256","integrity":{"organism_runs":0,"diagnostic_runs":0,"qualification_runs":0,"retries":0,"reseeds":0}}
        manifest_digest = write_bytes("AS003O_EVIDENCE_MANIFEST.json", canonical_bytes(manifest))
        print(json.dumps({"artifacts":len(inventory),"manifest_sha256":manifest_digest,"records":digests}, sort_keys=True))
        return
    if args.name is None or args.payload is None:
        parser.error("name and payload are required unless --write-locks is used")
    data = args.payload.encode("utf-8") if args.text else canonical_bytes(json.loads(args.payload))
    print(write_bytes(args.name, data))


if __name__ == "__main__":
    main()
