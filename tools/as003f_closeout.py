#!/usr/bin/env python3
"""AS-003F closeout evidence writer; no runtime imports or organism execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import uuid


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        offset = 0
        while offset < len(data):
            count = os.write(fd, data[offset:])
            if count <= 0:
                raise OSError("short_write")
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def write_text(root: Path, name: str, text: str) -> None:
    durable(root / name, text.encode())


def write_json(root: Path, name: str, value: object) -> None:
    write_text(root, name, json.dumps(value, indent=2, sort_keys=True) + "\n")


REQUIRED = [
    "AS003F_CONTEXT_OWNER_INVENTORY.json",
    "AS003F_OWNER_ACTIVATION_AUDIT.json",
    "AS003F_STATE_OPPORTUNITY_ACTIVATION_MAP.json",
    "AS003F_CONTEXT_LIFECYCLE_CONTRACT.md",
    "AS003F_PERSISTENCE_SWITCHING_AUDIT.json",
    "AS003F_DEACTIVATION_INTERRUPT_MAP.json",
    "AS003F_SIMULTANEOUS_CONTEXT_DATASET.json",
    "AS003F_SINGLE_CONTEXT_PROJECTION.json",
    "AS003F_CONTEXT_RESOLUTION_FAMILY_ANALYSIS.md",
    "AS003F_STARVATION_THRASHING_ANALYSIS.json",
    "AS003F_SOURCE_NEUTRALITY_CONTRACT.json",
    "AS003F_CONTEXT_IDENTITY_CONTRACT.json",
    "AS003F_PRIOR_ART_BOUNDARY.md",
    "AS003F_FROZEN_CORPUS_PROJECTIONS.json",
    "AS003F_GENERALITY_REVIEW.md",
    "AS003F_REPLACEMENT_CONTRACT.md",
    "AS003F_VERDICT.json",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    root = args.evidence_root
    missing = [name for name in REQUIRED if name != "AS003F_PRIOR_ART_BOUNDARY.md" and not (root / name).is_file()]
    if missing:
        raise SystemExit(f"missing_required_precloseout:{','.join(missing)}")
    if (root / "AS003F_PRIOR_ART_BOUNDARY.md").exists() or (root / "AS003F_EVIDENCE_MANIFEST.json").exists():
        raise SystemExit("closeout_artifact_already_exists")
    write_text(root, "AS003F_PRIOR_ART_BOUNDARY.md", """# AS-003F prior-art boundary

## Reference-only findings

- Palmer and Kristan review both external environmental context and internal/ongoing behavioral state as influences on behavioral choice. This supports an owner/context distinction, not a UMBRA priority equation. Source: https://pubmed.ncbi.nlm.nih.gov/21624826/.
- Burnett et al. report hunger-linked competition with rival drives whose expression depended on food accessibility. This supports the need to assess owner state and matching opportunity separately; it does not provide a universal activation rule or a transferable hierarchy. Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC5082717/.
- Cisek describes multiple currently available actions specified in parallel and biased until one response is selected. This supports preserved candidate specification and singleness of action without importing its neural mechanism or value signals. Source: https://pubmed.ncbi.nlm.nih.gov/17428779/.
- Faulkes observes that animals require ordered switching among behaviors. This supports treating persistence and switching as separate contract questions; it does not establish a resolver. Source: https://pubmed.ncbi.nlm.nih.gov/15378332/.

## Non-imports

No neural circuit topology, attractor model, dopamine/gain model, reinforcement learning, model-based RL, global utility, expected reward, motivational weight, fixed priority, active inference, POMDP, MPC, planner, rollout, or simulator was adopted. These sources bound the question only.

## AS-003F disposition

The literature is consistent with owner-local state, context/opportunity interaction, persistence, and switching, but supplies no ready-made source-neutral categorical election fact for UMBRA. It does not reduce the need to state a cross-owner simultaneous-context resolver explicitly.
""")
    write_text(root, "AS003F_PROJECTION_INTERPRETATION_ADDENDUM.md", """# AS-003F projection interpretation addendum

The sealed corpus records five lock-visible coactivation decisions (development practice plus memory recall, ticks 45–49 of Diagnostic A), not routine widespread context coactivation. Therefore the corpus does **not** establish that stochastic context election would already be de facto authority. It also cannot establish the opposite across temporal, social, routine, individuality, and non-hard physiology because those owner states are underrepresented or unavailable in retained A/B traces.

Accordingly, AS-003F does not adopt stochastic context election. It remains a possible residual-indifference family only after a future contract proves that it is rare across the protected owner scope and that initial election, persistence, and starvation boundaries are well defined. The terminal verdict rests on the missing owner-independent simultaneous-context proposition, not on a claim that stochasticity was already dominant in this limited corpus.
""")
    fixtures = {
        "schema": "AS003F_STATIC_SIMULTANEOUS_CONTEXT_FIXTURE_AUDIT_V1",
        "generated_at": now(),
        "method": "Source/qualified-fixture architecture review only. No runtime test, organism construction, or synthetic subsystem values were used.",
        "fixtures": [
            {"pairing": "physiology + temporal", "status": "UNQUALIFIED_COMBINATION", "facts": ["physiology hard recovery is protected", "temporal has versioned policy views"], "gap": "no locked non-hard physiology activation identity / shared resolver"},
            {"pairing": "physiology + social", "status": "UNQUALIFIED_COMBINATION", "facts": ["social requires current cue/context", "hard physiology interrupts unconditionally"], "gap": "no retained social activation and no non-hard resolver"},
            {"pairing": "physiology + habit", "status": "UNQUALIFIED_COMBINATION", "facts": ["routine needs valid binding", "physiology supplies hard authority"], "gap": "no non-hard physiology engagement condition"},
            {"pairing": "temporal + habit", "status": "STATIC_OWNER_SEMANTICS_ONLY", "facts": ["temporal ACTIVE/open semantics", "routine eligibility/binding"], "gap": "no owner-independent initial election"},
            {"pairing": "social + development", "status": "STATIC_OWNER_SEMANTICS_ONLY", "facts": ["social proposal eligibility", "development selected practice goal"], "gap": "no retained coactivation and no resolver"},
            {"pairing": "incumbent + newly active rival", "status": "CONTRACT_BOUNDARY_ONLY", "facts": ["owner revalidation can preserve incumbent", "hard interruption is protected"], "gap": "no common non-hard yield/preemption fact"},
            {"pairing": "two newly active contexts with no incumbent", "status": "FROZEN_CORPUS_OBSERVED", "facts": ["development + memory occurred for five retained decisions", "no hard interruption"], "gap": "no engaged identity or common categorical election"},
            {"pairing": "deactivation while rival remains active", "status": "STATIC_OWNER_SEMANTICS_ONLY", "facts": ["each owner has completion/invalidity paths"], "gap": "no retained paired deactivation row"},
            {"pairing": "hard recovery interrupts engaged non-hard context", "status": "PROTECTED_STATIC_SEMANTICS", "facts": ["critical/active recovery remains outside non-hard competition"], "gap": "no retained engaged-context identity"},
            {"pairing": "previous context executable after interruption", "status": "CONTRACT_BOUNDARY_ONLY", "facts": ["owner revalidation is required before resumption"], "gap": "no persisted context state exists currently"},
        ],
    }
    write_json(root, "AS003F_STATIC_SIMULTANEOUS_CONTEXT_FIXTURE_AUDIT.json", fixtures)
    all_files = sorted([p.name for p in root.iterdir() if p.is_file() and p.name != "AS003F_EVIDENCE_MANIFEST.json"])
    manifest = {"schema": "AS003F_FINAL_EVIDENCE_MANIFEST_V1", "generated_at": now(), "closeout_commit": args.commit, "required_files": {name: sha(root / name) for name in REQUIRED}, "additional_files": {name: sha(root / name) for name in all_files if name not in REQUIRED}, "required_file_count": len(REQUIRED), "durability": "file fsync, atomic rename, directory fsync, readback SHA-256", "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}}
    write_json(root, "AS003F_EVIDENCE_MANIFEST.json", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
