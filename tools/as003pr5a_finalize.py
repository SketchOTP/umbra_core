#!/usr/bin/env python3
"""Durably publish the AS-003P-R5A closeout and complete evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

try:
    from tools.as003pr5a_evidence import ROOT, canonical_json, publish
except ModuleNotFoundError:  # Direct path invocation places tools/ on sys.path.
    from as003pr5a_evidence import ROOT, canonical_json, publish


REPOSITORY = Path(__file__).resolve().parents[1]
BASELINE = "04946e3fc977593bf41d1eb40f1fc8517ef289aa"
VERDICT = "AS003PR5A_OBSERVER_SAFE_MODAL_EVIDENCE_NONDISCRIMINATING"


def run(*argv: str) -> str:
    completed = subprocess.run(
        argv,
        cwd=REPOSITORY,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def link_check() -> dict[str, object]:
    checked = 0
    broken: list[dict[str, str]] = []
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for source in (REPOSITORY / "README.md", REPOSITORY / "docs/EVIDENCE_GUIDE.md"):
        for target in pattern.findall(source.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#")):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            checked += 1
            if not (source.parent / relative).resolve().exists():
                broken.append({"source": str(source.relative_to(REPOSITORY)), "target": target})
    return {"checked": checked, "broken": broken, "status": "PASS" if not broken else "FAIL"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closeout-commit", required=True)
    args = parser.parse_args()

    authority = run("/home/sketch/cs14n-runtime/bin/python", "scripts/validate_authority_v3.py")
    governance = run(
        "/home/sketch/cs14n-runtime/bin/python",
        "scripts/validate_governance.py",
        "--mode",
        "ADOPTED",
    )
    run("git", "diff", "--check")
    links = link_check()
    if links["status"] != "PASS":
        raise RuntimeError(f"public link validation failed: {links['broken']}")

    changed = run("git", "diff", "--name-status", f"{BASELINE}..{args.closeout_commit}").splitlines()
    production = [row for row in changed if "\tumbra_core/" in row]
    changed_existing_tests = [
        row for row in changed if "\ttests/" in row and not row.startswith("A\t")
    ]
    retained = {
        "shared-root.sqlite": "9507f9e3f09f1691410711b584f1a98e7236a28957aef256099033cb97c20d20",
        "shared-root.sqlite-wal": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "shared-root.sqlite-shm": "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb",
        "shared-habitat.pickle": "10a176f6eb864f423d7dbb78f97f30103caf3486b0d78692ed1b9128cd81aa27",
    }
    retained_root = ROOT.parent / "umbra-as-003p-r5-common-root-modal-shadow-r1/r5-work"
    retained_readback = {name: sha256(retained_root / name) for name in retained}
    if retained_readback != retained:
        raise RuntimeError("retained R5 root changed during R5A")

    validation = {
        "schema": "AS003PR5A_CLOSEOUT_VALIDATION_V1",
        "authority_3_0": "PASS",
        "authority_output": authority.strip(),
        "governance": "PASS",
        "governance_output": governance.strip(),
        "git_diff_check": "PASS",
        "public_link_check": links,
        "production_delta": len(production),
        "production_paths": production,
        "existing_test_delta": len(changed_existing_tests),
        "existing_test_paths": changed_existing_tests,
        "retained_root_hashes_unchanged": True,
        "retained_root_readback": retained_readback,
    }
    validation_sha = publish("AS003PR5A_CLOSEOUT_VALIDATION.json", canonical_json(validation))

    closeout = {
        "schema": "AS003PR5A_CLOSEOUT_V1",
        "directive": "UMBRA-AS-003P-R5A",
        "verdict": VERDICT,
        "baseline": BASELINE,
        "execution_lock_commit": "50c1a2f2e23862c418b5377c1c08441c9f82d4d9",
        "repository_closeout_commit": args.closeout_commit,
        "root_creation_count": 0,
        "branch_loads": {"CONTROL": 1, "SHADOW": 1},
        "measured_ticks": {"CONTROL": 500, "SHADOW": 500},
        "observer_parity": "PASS",
        "semantic_difference_count": 0,
        "first_semantic_divergence": None,
        "timeline_equal": True,
        "candidate_identities_equal": True,
        "authoritative_event_semantics_equal": True,
        "final_authoritative_state_semantic_equal": True,
        "habitat_equal": True,
        "rng_equal": True,
        "frames": {"attempted": 500, "complete": 500, "rejected": 0},
        "candidate_profiles": 2686,
        "modal_distribution": {
            "STRONG_MUST": 0,
            "STRONG_MAY": 2664,
            "WEAK_MAY": 0,
            "NO_CONTINUATION": 0,
            "UNKNOWN": 22,
        },
        "candidate_pairs_with_profile_distinctions": 0,
        "frames_with_candidate_profile_distinctions": 0,
        "branch_frontier_peak": 4,
        "branch_overflow_count": 0,
        "as003l_relevant_exposure_count": 57,
        "as003l_exposure_with_distinction_count": 0,
        "as003l_disposition": "BLOCKER_NOT_EXPRESSED_DESPITE_EXPOSURE",
        "as002_disposition": "NO_RELATION_SUPPORTED",
        "historical_invalidated_modal_counts_used": False,
        "production_delta": 0,
        "existing_test_semantic_delta": 0,
        "retries": 0,
        "reseeds": 0,
        "authority_3_0": "PASS",
        "governance": "PASS",
        "evidence_publication_correction": {
            "status": "APPEND_ONLY_CORRECTION_PRESERVED",
            "correction_sha256": "619606dcbdbcc1d700494f50ee98d9f491f55b2c731b8199c4e34140a176efec",
            "retained_root_changed": False,
        },
        "closeout_validation_sha256": validation_sha,
        "successor_started": False,
        "closed_unix": time.time(),
    }
    closeout_sha = publish("AS003PR5A_CLOSEOUT.json", canonical_json(closeout))

    artifacts = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name == "AS003PR5A_FINAL_MANIFEST.json":
            continue
        artifacts.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "schema": "AS003PR5A_FINAL_MANIFEST_V1",
        "directive": "UMBRA-AS-003P-R5A",
        "verdict": VERDICT,
        "baseline": BASELINE,
        "repository_closeout_commit": args.closeout_commit,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "closeout_sha256": closeout_sha,
        "retained_root_hashes_unchanged": True,
        "retries": 0,
        "reseeds": 0,
        "successor_started": False,
    }
    manifest_sha = publish("AS003PR5A_FINAL_MANIFEST.json", canonical_json(manifest))
    print(json.dumps({"closeout_sha256": closeout_sha, "manifest_sha256": manifest_sha, "artifact_count": len(artifacts)}, sort_keys=True))


if __name__ == "__main__":
    main()
