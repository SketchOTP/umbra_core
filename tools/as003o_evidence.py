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
import tempfile


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
    if args.name is None or args.payload is None:
        parser.error("name and payload are required unless --write-locks is used")
    data = args.payload.encode("utf-8") if args.text else canonical_bytes(json.loads(args.payload))
    print(write_bytes(args.name, data))


if __name__ == "__main__":
    main()
