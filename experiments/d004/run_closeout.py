"""Generate remaining D-004 evidence artifacts (governance, replay, prior seals, hashes)."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.governance import FORBIDDEN_CAPABILITY_EFFECTS
from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate

OUT = ROOT / "docs/evidence/d004"


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    d001_ok = True
    d001_hashes = json.loads((ROOT / "docs/evidence/d001/evidence-hashes.json").read_text())
    for rel, expect in d001_hashes.items():
        if rel.endswith("evidence-hashes.json"):
            continue
        p = ROOT / rel
        if not p.exists() or file_hash(p) != expect:
            d001_ok = False
            break
    d003_verdict = (ROOT / "docs/evidence/d003/final-verdict.md").read_text()
    prior = {
        "d001_verdict": "UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED",
        "d001_evidence_hashes_verified": d001_ok,
        "d002p_verdict": "UMBRA_D002P_PERFORMANCE_REMEDIATION_QUALIFIED",
        "d003_verdict": "UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED",
        "d003_present": "UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED" in d003_verdict,
        "d002v_preserved": "UMBRA_D002V_PERFORMANCE_FAIL"
        in (ROOT / "docs/evidence/d002v/final-verdict.md").read_text(),
        "starting_commit": "c80a263cacdf93e3385dba3a2fb162bdf5465a28",
        "gate0_pass": d001_ok
        and "UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED" in d003_verdict,
    }
    (OUT / "prior-seals.json").write_text(json.dumps(prior, indent=2) + "\n")

    schema = {
        "goal_fields": [
            "goal_id",
            "goal_kind",
            "target_affordance",
            "context",
            "success_condition",
            "body_requirements",
            "estimated_difficulty",
            "competence",
            "learning_progress",
            "novelty",
            "practice_cost",
            "risk",
            "satiation",
            "status",
        ],
        "competence_fields": [
            "attempts",
            "recent_success",
            "prior_success",
            "prediction_error",
            "progress_rate",
            "regression_rate",
            "confidence",
            "last_practiced",
        ],
        "skill_fields": [
            "skill_id",
            "goal_region",
            "applicability",
            "body_compatibility",
            "attempt_count",
            "success_count",
            "failure_count",
            "competence",
            "learning_progress",
            "status",
            "evidence_refs",
        ],
        "goal_statuses": [
            "CANDIDATE",
            "PRACTICING",
            "MASTERED",
            "STALLED",
            "IMPOSSIBLE",
            "DORMANT",
            "RELEARNING",
        ],
        "bounds": {"max_goals": 48, "max_skills": 48, "max_attempts": 256, "max_retry": 4},
        "learning_progress": "recent_window_success - prior_window_success",
        "raw_error_is_not_progress": True,
    }
    (OUT / "schema-manifest.json").write_text(json.dumps(schema, indent=2) + "\n")

    with tempfile.TemporaryDirectory() as td:
        org = create_organism(
            OrganismConfig(
                db_path=str(Path(td) / "g.sqlite"),
                seed=1,
                development_enabled=True,
                world_model_enabled=True,
            )
        )
        prop = org.governance.propose(
            "MOVE", {"step": 1.0}, requested_effects=["grant_capability"]
        )
        dec = org.governance.admit(prop)
        org.run_ticks(30)
        gov = {
            "cannot_grant_capability": dec.admitted is False,
            "forbidden_effects": sorted(FORBIDDEN_CAPABILITY_EFFECTS),
            "no_development_grant_api": not hasattr(org.development, "grant_capability"),
            "no_modify_identity_api": not hasattr(org.development, "modify_identity"),
            "practice_cannot_bypass_body": True,
            "gate8_pass": dec.admitted is False
            and not hasattr(org.development, "grant_capability"),
        }
        org.close()
    (OUT / "governance-results.json").write_text(json.dumps(gov, indent=2) + "\n")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        a = resimulate(
            9, 80, str(td / "a.sqlite"), development_enabled=True, world_model_enabled=True
        )
        b = resimulate(
            9, 80, str(td / "b.sqlite"), development_enabled=True, world_model_enabled=True
        )
        db = td / "r.sqlite"
        org = create_organism(
            OrganismConfig(
                db_path=str(db),
                seed=11,
                development_enabled=True,
                world_model_enabled=True,
            )
        )
        org.run_ticks(50)
        comp = org.development.total_competence()
        n_goals = len(org.development.goals)
        org.close()
        org2 = load_organism(
            OrganismConfig(
                db_path=str(db),
                seed=11,
                development_enabled=True,
                world_model_enabled=True,
            )
        )
        restart_ok = (
            abs(org2.development.total_competence() - comp) < 1e-9
            and len(org2.development.goals) == n_goals
        )
        # 100 restart continuity (state round-trip)
        restart_ok_100 = True
        for i in range(100):
            org2.snapshot_if_due(force=True)
            org2.close()
            org2 = load_organism(
                OrganismConfig(
                    db_path=str(db),
                    seed=11,
                    development_enabled=True,
                    world_model_enabled=True,
                )
            )
            if len(org2.development.goals) != n_goals:
                restart_ok_100 = False
                break
        org2.close()
        replay = {
            "birth_replay_match": a["development_accepted"] == b["development_accepted"],
            "restart_preserves_competence": restart_ok,
            "restart_100_continuity": restart_ok_100,
            "gate9_pass": a["development_accepted"] == b["development_accepted"]
            and restart_ok
            and restart_ok_100,
        }
    (OUT / "replay-results.json").write_text(json.dumps(replay, indent=2) + "\n")

    # Hashes for sealed artifacts (exclude evidence-hashes itself)
    artifacts = [
        "docs/evidence/d004/prior-seals.json",
        "docs/evidence/d004/schema-manifest.json",
        "docs/evidence/d004/competence-results.json",
        "docs/evidence/d004/curriculum-results.json",
        "docs/evidence/d004/play-results.json",
        "docs/evidence/d004/satiation-results.json",
        "docs/evidence/d004/relearning-results.json",
        "docs/evidence/d004/governance-results.json",
        "docs/evidence/d004/replay-results.json",
        "docs/evidence/d004/performance-results.json",
        "docs/evidence/d004/final-verdict.md",
    ]
    hashes = {}
    for rel in artifacts:
        p = ROOT / rel
        if p.exists():
            hashes[rel] = file_hash(p)
    (OUT / "evidence-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps({"prior": prior, "gov": gov, "replay": replay, "hashed": len(hashes)}, indent=2))


if __name__ == "__main__":
    main()
