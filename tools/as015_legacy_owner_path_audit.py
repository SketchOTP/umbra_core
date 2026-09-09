"""Trace legacy protected assertions through their current authority paths.

Development-only roots use the historical test seeds and are not qualification
evidence.  The audit records whether each fixed-horizon assertion actually
reaches the authority transition it claims to assess.
"""

from __future__ import annotations

import importlib.util
import tempfile
from collections import Counter
from pathlib import Path

from tools.as015_evidence import publish


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _events(org):
    return list(org.store.iter_events())


def _d003_case(helper, root: Path, seed: int, intervention: str, ticks: int, **phys):
    org = helper(root, seed, world_intervention=intervention)
    try:
        org.phys.intervene(**phys)
        org.run_ticks(ticks)
        events = _events(org)
        verified = [e for e in events if e["event_type"] == "outcome_verified"]
        capabilities = Counter(str(e["payload"].get("capability")) for e in verified)
        charge = [e for e in verified if e["payload"].get("capability") == "CHARGE"]
        return {
            "seed": seed,
            "intervention": intervention,
            "ticks": ticks,
            "verified_capability_counts": dict(sorted(capabilities.items())),
            "verified_charge_outcomes": len(charge),
            "verified_charge_failures": sum(not bool(e["payload"].get("success")) for e in charge),
            "charge_models": [m.to_dict() for m in org.world_model.models.values() if m.action == "CHARGE"],
            "charge_affordances": [a.to_dict() for a in org.world_model.affordances.values() if a.action == "charge_from"],
            "contradictions": [c for c in org.world_model.contradictions if c.get("action") == "CHARGE"],
            "supersessions": [s for s in org.world_model.live_supersessions() if s.get("action") == "CHARGE"],
            "conclusion": "NO_CHARGE_CONTRADICTION_REACHED" if not charge else "CHARGE_PATH_REACHED",
        }
    finally:
        org.close()


def _d006_case(helper, root: Path):
    org = helper(root)
    try:
        org.embodiment.body.x = 11.0
        org.embodiment.body.y = 8.0
        rows = []
        for _ in range(10):
            org.tick_once()
            events = _events(org)
            proposals = [e["payload"] for e in events if e["event_type"] == "proposal"]
            signals = [p for p in proposals if p.get("capability") in {"SIGNAL_PLAY", "SIGNAL_ASSISTANCE"}]
            rows.append({
                "tick": org.tick,
                "hypotheses": len(org.social.hypotheses),
                "pending": len(org.social.pending),
                "signal_proposals": signals,
                "selected_capability": proposals[-1].get("capability") if proposals else None,
            })
        event_types = Counter(e["event_type"] for e in _events(org))
        return {
            "ticks": rows,
            "event_type_counts": dict(sorted(event_types.items())),
            "social_pending_created": int(event_types["social_pending_created"]),
            "conclusion": "NO_SOCIAL_SIGNAL_SELECTED" if not any(r["signal_proposals"] for r in rows) else "SOCIAL_SIGNAL_PATH_REACHED",
        }
    finally:
        org.close()


def _d009_case(module):
    from umbra_core.arbitration import Arbitrator
    from umbra_core.physiology import Physiology
    from umbra_core.util import SeededRNG

    _, _, perception, _, _ = module._task7_habitat_setup()
    bindings = perception.policy_view()["manipulation_bindings"]
    phys = Physiology()
    phys.energy = 0.31
    arb = Arbitrator()
    observations = [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 1.0}]
    manip = [m.to_candidate() for m in arb.generate_manipulation_candidates(bindings, phys, 1)]
    ordinary = arb.generate_candidates(phys, observations, 1)
    scored = [arb.score_candidate(c, phys, observations, 1) for c in [*ordinary, *manip]]
    chosen = arb.select(phys, observations, tick=1, rng=SeededRNG(7), manipulation_bindings=bindings)
    return {
        "policy_visible_binding_count": len(bindings),
        "manipulation_candidates": [
            {"capability": c.capability, "params": dict(c.params)} for c in manip
        ],
        "scored_capabilities": [{"capability": c.capability, "total": c.total, "params": c.params} for c in scored],
        "chosen": {"capability": chosen.capability, "params": dict(chosen.params)},
        "conclusion": "MANIPULATION_PARTICIPATES_BUT_DOES_NOT_WIN_FIXED_SELECTOR" if manip and chosen.capability != "MANIPULATE" else "MANIPULATION_PATH_MISSING",
    }


def main() -> None:
    d003 = _load("as015_d003", "tests/test_d003.py")
    d006 = _load("as015_d006", "tests/test_d006.py")
    d009 = _load("as015_d009", "tests/test_d009.py")
    with tempfile.TemporaryDirectory(prefix="as015-owner-path-") as temporary:
        root = Path(temporary)
        payload = {
            "directive": "UMBRA-AS-015",
            "classification_boundary": "development-only source-path audit; no formal seed or scientific lock",
            "d003": [
                _d003_case(d003._wm_org, root, 7, "I6", 150, energy=0.15, stimulation=0.5),
                _d003_case(d003._wm_org, root, 10, "I10", 160, energy=0.12, fatigue=0.2),
                _d003_case(d003._wm_org, root, 15, "I6", 180, energy=0.12),
            ],
            "d006": _d006_case(d006._soc_org, root),
            "d009": _d009_case(d009),
            "d010": {
                "inventory_contract": "current Q4 scanner is line-number keyed against a historical registry; baseline differential shows the registry was already stale before AS-014/AS-015",
                "adaptive_trim_contract": "current implementation invokes native-arena release only after observed expression-path RSS growth; allocator release is best-effort, while qualified performance claims are governed RSS bounds",
            },
        }
    print(publish("AS015_LEGACY_OWNER_PATH_AUDIT.json", payload))


if __name__ == "__main__":
    main()
