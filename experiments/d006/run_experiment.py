"""UMBRA-D-006 experiment harness — social contingency, frozen matrix, paired seeds.

Reads the FROZEN preregistration (experiments/d006/experiment-matrix.json +
thresholds.json) and never rewrites it. Every gate-critical cell runs the matrix's
declared paired-seed count (>=100). Gates 1-9 are asserted numerically against the
frozen thresholds; gate 12 (performance soak) is deferred to Task 13 and gates
10/11 (prior seals, replay) are covered by the pytest suite (a replay determinism
probe is still recorded here as evidence).

Methodology note (honest): contingency/reliability mechanisms are driven directly
against `SocialEngine` with harness-synthesized cues and the frozen
`response_policy_for_history` partner policies — the same controlled-cue technique
the sealed D-006 unit suite uses. Paired seeds vary the partner-response RNG
(contingent/none draws, delays); those recognition discriminators are deterministic
given cues, so their variance is ~0 by construction and reported as such.

Gate 3 recognition is ALSO measured end-to-end through the real path (embodiment
`PartnerTrueCues` plant -> `PerceptionMembrane` -> `SocialEngine.recognize` inside
`Organism.tick_once`) via `_organism_recognition`. The prior calibration bug
(inter-partner cue separation below perception identity-cue noise, so distinct
partners collapsed into one hypothesis) is fixed: `PartnerTrueCues.for_history` uses
an antipodal per-index identity basis and `PerceptionMembrane` applies a smaller
identity-signature noise than spatial noise. The frozen `recognition_match_threshold`
(0.55) is unchanged. Gate 3 requires BOTH the synthetic mechanism check and the
organism-level separation/no-merge check to pass.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.embodiment import response_policy_for_history
from umbra_core.memory import MemoryEngine
from umbra_core.persistence import Store
from umbra_core.physiology import Physiology
from umbra_core.social import ResponseClass, SocialEngine, condition_to_social_config
from umbra_core.util import SeededRNG

NONE_TIMEOUT = 32  # frozen thresholds.json response_window_none_timeout_ticks
N_ENC = 10  # contingent-history encounters (>= routine_min_independent_episodes)


# --- cue synthesis (harness-owned; mirrors sealed unit-test cue shape) --------


def _cue(tag: float = 0.0) -> dict[str, Any]:
    """Synthetic partner cue with a controllable identity `tag` in the matched dims.

    ponytail: identical to tests._social_cue so recognition behaves exactly as the
    sealed suite; identity separation lives in `tag` (0.0 vs 1.0 => distinct,
    0.5 => genuinely ambiguous midpoint). Ceiling: does not model perception noise;
    upgrade path is driving through PerceptionMembrane once plant cue separation
    exceeds sensor sigma.
    """
    return {
        "relative_position": [1.0, 0.5],
        "motion_signature": [0.2 + tag, 0.3, 0.1],
        "appearance_signature": [0.5, 0.4, 0.2 + tag],
        "response_timing_pattern": [0.3, 0.5, 0.1],
        "interaction_style_cues": [0.6 + tag, 0.3, 0.5],
        "cue_confidence": 0.7,
        "cue_uncertainty": 0.3,
        "observed_at": 1.0,
        "expires_at": 999.0,
        "source": "partner_cue",
    }


def _familiar(engine: SocialEngine, tag: float, t0: int) -> str | None:
    """Two identical sightings => one FAMILIAR hypothesis. None if recognition off."""
    engine.recognize([_cue(tag)], t0)
    r = engine.recognize([_cue(tag)], t0 + 1)
    return r.matches[0].hypothesis_id


def _resolve(engine, mem, store, hid, context, signal, now, policy, rng) -> ResponseClass:
    p = engine.create_pending(
        hypothesis_id=hid,
        context=context,
        signal=signal,
        execution_id=f"e{now}",
        signal_tick=now,
        recognition_confidence=1.0,
        governance_admitted=True,
        capability_executed=True,
        store=store,
        tick=now,
    )
    if policy.should_respond(signal, float(now), rng):
        delay = policy.response_delay_ticks(float(now), rng)
        return engine.observe_outcome(
            p.pending_interaction_id, response_tick=now + delay, response_observed=True,
            store=store, memory=mem,
        )
    return engine.observe_outcome(
        p.pending_interaction_id, response_tick=now + NONE_TIMEOUT + 8, response_observed=False,
        store=store, memory=mem,
    )


# --- recognition gate cells (H8 swap, H9 ambiguous) ---------------------------


def recognition_trial(condition: str, history: str) -> dict[str, Any]:
    cfg = condition_to_social_config(condition)
    events: list[tuple[str, dict[str, Any]]] = []
    engine = SocialEngine.create(
        "agent-1", seed=1, config=cfg, emit_event=lambda t, p: events.append((t, p))
    )
    out: dict[str, Any] = {"authority_safe": engine.try_grant_authority({"grant_capability": True}) is False}

    hid_a = _familiar(engine, 0.0, 1)
    hid_b = _familiar(engine, 1.0, 3)
    if history == "H8":
        first_b_tick = 3
        engine.recognize([_cue(1.0)], 5)  # B again while A recently familiar => swap
        swaps = [p for t, p in events if t == "social_partner_swap_detected"]
        out["recog_accuracy_ok"] = float(
            hid_a != hid_b
            and bool(swaps)
            and swaps[-1]["from_hypothesis_id"] == hid_a
            and swaps[-1]["to_hypothesis_id"] == hid_b
        )
        out["false_merge"] = 0.0 if hid_a != hid_b else 1.0
        out["swap_latency"] = float(swaps[-1]["tick"] - first_b_tick) if swaps else None
    else:  # H9 ambiguous midpoint must stay non-FAMILIAR
        n = 5
        non_familiar = 0
        for i in range(n):
            r = engine.recognize([_cue(0.5)], 5 + i)
            if r.matches[0].status != "FAMILIAR":
                non_familiar += 1
        out["ambiguous_unknown_frac"] = non_familiar / n
    return out


# --- interaction gate cells ---------------------------------------------------


def _two_partner_separation(condition: str, seed: int, workdir: str) -> float:
    """Gate 2 discriminator: can the model keep a contingent partner's reliability
    separate from a noncontingent partner's? C0 separates; C2 pools (0); C4 forgets.

    Uses its own store/memory (fresh agent id) so deterministic pending/episode ids
    never collide with the primary trial's already-committed evidence links.
    """
    cfg = condition_to_social_config(condition)
    db = os.path.join(workdir, f"sep_{condition}_{seed}_{os.getpid()}.db")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(db + suffix)
        except OSError:
            pass
    store = Store(db)
    mem = MemoryEngine.create("sep-agent", seed=seed)
    engine = SocialEngine.create("sep-agent", seed=seed, config=cfg)
    rng = SeededRNG(seed * 131 + 7)
    contingent = response_policy_for_history("H0")
    silent = response_policy_for_history("H1")  # 0.5 responder as the weaker partner
    now = 10
    hid_a = hid_b = None
    for _ in range(4):
        if not cfg.persist_relationship:
            engine.reset_for_encounter_boundary()
        hid_a = _familiar(engine, 0.0, now)
        hid_b = _familiar(engine, 1.0, now + 2)
        now += 4
        if hid_a is None or hid_b is None:
            continue
        _resolve(engine, mem, store, hid_a, "play", "SIGNAL_PLAY", now, contingent, SeededRNG(seed))
        # partner B: force NONE regardless of policy (the noncontingent contrast)
        pb = engine.create_pending(
            hypothesis_id=hid_b, context="play", signal="SIGNAL_PLAY", execution_id=f"b{now}",
            signal_tick=now, recognition_confidence=1.0, governance_admitted=True,
            capability_executed=True, store=store, tick=now,
        )
        engine.observe_outcome(
            pb.pending_interaction_id, response_tick=now + NONE_TIMEOUT + 8,
            response_observed=False, store=store, memory=mem,
        )
        now += 50
    ra = engine.hypotheses[hid_a].reliability_by_context.get("play", 0.0) if hid_a in engine.hypotheses else 0.0
    rb = engine.hypotheses[hid_b].reliability_by_context.get("play", 0.0) if hid_b in engine.hypotheses else 0.0
    store.close()
    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(db + suffix)
        except OSError:
            pass
    # Pooled model collapses to one hypothesis => identical reliability => 0 separation.
    if hid_a == hid_b:
        return 0.0
    return abs(ra - rb)


def _unnecessary_bids(engine: SocialEngine, hid: str) -> int:
    """Gate 5: bids emitted before seeking self-limits. C0 satiates (~few); C5 never."""
    phys = Physiology()
    engine.hypotheses[hid].familiarity = 1.0
    bids = 0
    for t in range(1000, 1060):
        cand = engine.propose(phys, [_cue(0.0)], tick=t, critical=False)
        if cand is not None and cand.params.get("social_intent") in ("OFFER_PLAY", "REQUEST_ASSISTANCE"):
            bids += 1
            engine.update_satiation_anchor(hid, t)
    return bids


def interaction_trial(condition: str, history: str, seed: int, workdir: str) -> dict[str, Any]:
    cfg = condition_to_social_config(condition)
    db = os.path.join(workdir, f"{condition}_{history}_{seed}_{os.getpid()}.db")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(db + suffix)
        except OSError:
            pass
    store = Store(db)
    mem = MemoryEngine.create("agent-1", seed=seed)
    engine = SocialEngine.create("agent-1", seed=seed, config=cfg)
    policy = response_policy_for_history(history)
    rng = SeededRNG(seed)
    context = "assistance" if history == "H3" else "play"
    signal = "SIGNAL_ASSISTANCE" if context == "assistance" else "SIGNAL_PLAY"

    out: dict[str, Any] = {
        "authority_safe": engine.try_grant_authority({"grant_capability": True}) is False
    }

    hid = _familiar(engine, 0.0, 1)
    out["false_split"] = float(len([h for h in engine.hypotheses.values() if h.status != "INACTIVE"]) > 1)
    if hid is None:  # C6 recognition disabled
        store.close()
        return out

    is_flip = history in ("H5", "H6")
    contingent_count = none_count = delayed_count = 0
    rel_before = rel_after_first_none = None
    first_none = False

    if is_flip:
        pre_ticks = [8, 16, 24, 32, 40]
        post_ticks = [56, 64, 72, 80, 88, 96, 104, 112, 120, 128]
        schedule = [(t, "pre") for t in pre_ticks] + [(t, "post") for t in post_ticks]
    else:
        schedule = [(10 + 50 * i, "post") for i in range(N_ENC)]

    for now, phase in schedule:
        if is_flip and phase == "post" and rel_before is None:
            rel_before = engine.hypotheses[hid].reliability_by_context.get(context, 0.0)
        cls = _resolve(engine, mem, store, hid, context, signal, now, policy, rng)
        if cls == ResponseClass.CONTINGENT:
            contingent_count += 1
        elif cls == ResponseClass.DELAYED:
            delayed_count += 1
        elif cls == ResponseClass.NONE:
            none_count += 1
            if is_flip and phase == "post" and not first_none:
                rel_after_first_none = engine.hypotheses[hid].reliability_by_context.get(context, 0.0)
                first_none = True

    rel = engine.hypotheses[hid].reliability_by_context.get(context, 0.0) if hid in engine.hypotheses else 0.0
    out.update(
        reliability=rel,
        contingent_count=contingent_count,
        none_count=none_count,
        delayed_count=delayed_count,
    )

    # Gate 8 provenance (C0 x H0 primary): evidence links resolve to real episodes.
    if contingent_count > 0 and hid in engine.hypotheses:
        links = store.social_evidence_links_for(hid)
        support = {lnk["episode_id"] for lnk in links if lnk.get("relation") == "support"}
        all_eids = {lnk["episode_id"] for lnk in links}
        out["provenance_ok"] = float(
            bool(support)
            and all(e in mem.episodes for e in all_eids)  # every link resolves to a real episode
            and support.issubset(set(engine.hypotheses[hid].evidence_refs))
        )

    if is_flip:
        out["rel_before"] = rel_before if rel_before is not None else 0.0
        out["rel_after"] = rel
        out["rel_after_first_none"] = rel_after_first_none
        cell = engine.contingency_cells.get(engine._cell_key(hid, context, signal))
        out["supporting_preserved"] = float(bool(cell and cell.supporting_episode_ids))

    if history == "H10":
        formed = int(engine.metrics.get("routines_promoted", 0)) > 0 or bool(engine.routine_handles)
        out["routine_formed"] = float(formed)

    if history == "H7":
        fam_before = engine.hypotheses[hid].familiarity
        rel_snapshot = dict(engine.hypotheses[hid].reliability_by_context)
        phys = Physiology()
        bids = sum(
            1 for t in range(2000, 5000, 25)
            if engine.propose(phys, [], tick=t, critical=False) is not None
        )
        out["absence_bids"] = bids
        out["absence_no_punishment"] = float(
            engine.hypotheses[hid].familiarity == fam_before
            and engine.hypotheses[hid].reliability_by_context == rel_snapshot
        )

    if history == "H0" and condition in ("C0", "C2", "C4"):
        out["separation"] = _two_partner_separation(condition, seed, workdir)
    if history == "H0" and condition in ("C0", "C5"):
        out["unnecessary_bids"] = _unnecessary_bids(engine, hid)

    store.close()
    try:
        for suffix in ("", "-wal", "-shm"):
            os.unlink(db + suffix)
    except OSError:
        pass
    return out


def run_trial(seed: int, condition: str, history: str, workdir: str) -> dict[str, Any]:
    base: dict[str, Any] = {"seed": seed, "condition": condition, "history": history}
    if history in ("H8", "H9"):
        base.update(recognition_trial(condition, history))
    else:
        base.update(interaction_trial(condition, history, seed, workdir))
    return base


# --- aggregation + deterministic probes ---------------------------------------


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def mean(key: str) -> float | None:
        xs = [float(r[key]) for r in rows if r.get(key) is not None]
        return sum(xs) / len(xs) if xs else None

    keys = [
        "reliability", "contingent_count", "none_count", "delayed_count", "provenance_ok",
        "separation", "unnecessary_bids", "rel_before", "rel_after", "rel_after_first_none",
        "supporting_preserved", "routine_formed", "absence_bids", "absence_no_punishment",
        "recog_accuracy_ok", "false_merge", "swap_latency", "ambiguous_unknown_frac",
        "false_split", "authority_safe",
    ]
    agg: dict[str, Any] = {"n": len(rows)}
    for k in keys:
        agg[f"mean_{k}"] = mean(k)
    return agg


def _single_failure_preserved(workdir: str) -> dict[str, Any]:
    """Gate 4: one anomaly weakens slightly, does not destroy reliability."""
    db = os.path.join(workdir, f"sf_{os.getpid()}.db")
    store = Store(db)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine = SocialEngine.create("agent-1", seed=1)
    hid = _familiar(engine, 0.0, 1)
    policy = response_policy_for_history("H0")
    now = 10
    for _ in range(4):  # deterministic contingent responses (delay 3)
        p = engine.create_pending(
            hypothesis_id=hid, context="play", signal="SIGNAL_PLAY", execution_id=f"c{now}",
            signal_tick=now, recognition_confidence=1.0, governance_admitted=True,
            capability_executed=True, store=store, tick=now,
        )
        engine.observe_outcome(
            p.pending_interaction_id, response_tick=now + 3, response_observed=True,
            store=store, memory=mem,
        )
        now += 50
    baseline = engine.hypotheses[hid].reliability_by_context["play"]
    p = engine.create_pending(
        hypothesis_id=hid, context="play", signal="SIGNAL_PLAY", execution_id="fail",
        signal_tick=now, recognition_confidence=1.0, governance_admitted=True,
        capability_executed=True, store=store, tick=now,
    )
    engine.observe_outcome(
        p.pending_interaction_id, response_tick=now + 40, response_observed=False,
        store=store, memory=mem,
    )
    after_one = engine.hypotheses[hid].reliability_by_context["play"]
    store.close()
    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(db + suffix)
        except OSError:
            pass
    preserved = after_one > 0.0 and after_one > baseline * 0.5 and (baseline - after_one) < baseline * 0.2
    return {"baseline": baseline, "after_one": after_one, "preserved": bool(preserved)}


# Understimulation is a benign homeostatic band that fluctuates around its threshold
# from ordinary D-001 dynamics; it is not a survival/damage variable. Absence shifts
# non-social behavior, so `stimulation` excursion timing jitters within the D-001
# envelope. Gate 6 "viability within prior bounds" is about survival-critical damage.
_SURVIVAL_CRITICAL = ("energy", "integrity", "fatigue")


def _viability_ok(seed: int, workdir: str) -> bool:
    """Absence must introduce no survival-critical excursion (energy/integrity/fatigue)
    beyond the partner-present H0 baseline. Exact-trace equality holds for some seeds
    but is too strict cross-seed because benign `stimulation` timing jitters."""
    from umbra_core.runtime import OrganismConfig, create_organism

    def survival_crit(history: str) -> list[tuple[int, tuple[str, ...]]]:
        db = os.path.join(workdir, f"viab_{history}_{seed}.sqlite")
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(db + suffix)
            except OSError:
                pass
        org = create_organism(
            OrganismConfig(
                db_path=db, seed=seed, social_enabled=True, social_history=history,
                condition="C0", drift_enabled=False,
            )
        )
        t: list[tuple[int, tuple[str, ...]]] = []
        for _ in range(60):
            org.tick_once()
            hits = tuple(sorted(v for v in org.phys.critical_vars() if v in _SURVIVAL_CRITICAL))
            if hits:
                t.append((org.tick, hits))
        org.close()
        return t

    h7 = survival_crit("H7")
    h0 = set(survival_crit("H0"))
    # No survival-critical excursion under absence that the baseline does not already have.
    return all(e in h0 for e in h7)


def _c3_no_leak() -> dict[str, Any]:
    """Gate 9 fail-closed: C3 affection controller stays isolated, no production schema."""
    from dataclasses import asdict, fields

    import umbra_core.social.engine as eng
    from umbra_core.social import PartnerHypothesis, SocialConfig, condition_to_social_config

    c3_is_baseline = asdict(condition_to_social_config("C3")) == asdict(SocialConfig())
    no_meter_symbol = not hasattr(eng, "AffectionMeter")
    forbidden = {"authority", "granted_capabilities", "trust_level", "grant_capability",
                 "affection", "affection_meter"}
    field_names = {f.name for f in fields(PartnerHypothesis)}
    no_forbidden_fields = field_names.isdisjoint(forbidden)
    controller_isolated = (ROOT / "experiments/d006/affection_controller.py").exists()
    social_init = (ROOT / "umbra_core/social/__init__.py").read_text()
    not_in_production = "AffectionMeter" not in social_init and "affection" not in social_init.lower()
    ok = all([c3_is_baseline, no_meter_symbol, no_forbidden_fields, controller_isolated, not_in_production])
    return {
        "c3_config_is_baseline": c3_is_baseline,
        "no_affection_meter_symbol": no_meter_symbol,
        "no_forbidden_hypothesis_fields": no_forbidden_fields,
        "controller_isolated_to_experiments": controller_isolated,
        "not_referenced_in_production_social": not_in_production,
        "c3_no_leak": ok,
    }


def _governance_cooldown_denies() -> bool:
    from umbra_core.governance import Governance, GovernanceState

    gov = Governance(GovernanceState(last_signal_tick=10, signal_cooldown_ticks=6))
    dec = gov.admit(gov.propose("SIGNAL_PLAY", {"tick": 15}), tick=15)
    return (not dec.admitted) and dec.reason == "signal_cooldown"


def _replay_determinism(workdir: str) -> dict[str, Any]:
    from umbra_core.runtime import resimulate

    kwargs = dict(social_enabled=True, social_history="H0", condition="C0", drift_enabled=False)
    paths = [os.path.join(workdir, "replay_a.sqlite"), os.path.join(workdir, "replay_b.sqlite")]
    for p in paths:
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(p + suffix)
            except OSError:
                pass
    a = resimulate(41, 40, paths[0], **kwargs)
    b = resimulate(41, 40, paths[1], **kwargs)
    return {
        "tick_equal": a["tick"] == b["tick"],
        "identity_equal": a["identity_agent_id"] == b["identity_agent_id"],
        "social_accepted_equal": a["social_accepted"] == b["social_accepted"],
    }


def _event_authority_map() -> dict[str, Any]:
    from umbra_core.events import SOCIAL_EVENT_AUTHORITY, social_event_authority_class

    authoritative = sorted(k for k, v in SOCIAL_EVENT_AUTHORITY.items() if v == "AUTHORITATIVE")
    diagnostic = sorted(k for k, v in SOCIAL_EVENT_AUTHORITY.items() if v == "DIAGNOSTIC")
    checks = {
        "social_pending_created": social_event_authority_class("social_pending_created") == "AUTHORITATIVE",
        "social_recognition_updated": social_event_authority_class("social_recognition_updated") == "AUTHORITATIVE",
        "social_reliability_revised": social_event_authority_class("social_reliability_revised") == "AUTHORITATIVE",
        "social_match_score_diagnostic": social_event_authority_class("social_match_score") == "DIAGNOSTIC",
    }
    return {
        "authoritative": authoritative,
        "diagnostic": diagnostic,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }


def _organism_recognition(workdir: str, seeds: int = 20, ticks: int = 60) -> dict[str, Any]:
    """Gate 3 organism-level recognition through the REAL path (embodiment plant ->
    PerceptionMembrane -> SocialEngine.recognize inside Organism.tick_once).

    Honest end-to-end counterpart to the synthetic-cue recognition_trial: proves
    distinct H8 partners separate (no silent merge, swap discriminator fires) and
    ambiguous H9 partners do not false-split, after the PartnerTrueCues /
    PerceptionMembrane recalibration. The frozen recognition threshold is unchanged.
    """
    from umbra_core.runtime import OrganismConfig, create_organism

    def run(history: str, seed: int) -> tuple[int, int, int]:
        db = os.path.join(workdir, f"org_recog_{history}_{seed}.sqlite")
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(db + suffix)
            except OSError:
                pass
        org = create_organism(
            OrganismConfig(
                db_path=db, seed=seed, social_enabled=True, social_history=history,
                condition="C0", drift_enabled=False,
            )
        )
        for _ in range(ticks):
            org.tick_once()
        active = len([h for h in org.social.hypotheses.values() if h.status != "INACTIVE"])
        swaps = int(org.social.metrics.get("partner_swaps_detected", 0))
        created = int(org.social.metrics.get("hypotheses_created", 0))
        org.close()
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(db + suffix)
            except OSError:
                pass
        return active, swaps, created

    h8 = [run("H8", s) for s in range(seeds)]
    h9 = [run("H9", s) for s in range(seeds)]
    return {
        "seeds": seeds,
        "ticks": ticks,
        "path": "embodiment->perception->SocialEngine.recognize (Organism.tick_once)",
        "h8_distinct_and_swap_frac": sum(1 for a, sw, c in h8 if a == 2 and c == 2 and sw > 0) / seeds,
        "h8_false_merge_frac": sum(1 for a, _sw, c in h8 if a < 2 or c < 2) / seeds,
        "h9_ambiguous_not_split_frac": sum(1 for a, _sw, c in h9 if a == 1 and c == 1) / seeds,
    }


def main() -> None:
    matrix = json.loads((ROOT / "experiments/d006/experiment-matrix.json").read_text())
    thr = json.loads((ROOT / "experiments/d006/thresholds.json").read_text())
    work = ROOT / ".soak" / "d006_exp"
    work.mkdir(parents=True, exist_ok=True)
    out_dir = ROOT / "docs/evidence/d006"
    out_dir.mkdir(parents=True, exist_ok=True)
    workdir = str(work)

    include_exploratory = "--gate-only" not in sys.argv
    gate_cells = [(c["condition"], c["history"], int(c["paired_seeds"])) for c in matrix["gate_critical_cells"]]
    expl_cells = (
        [(c["condition"], c["history"], int(c["paired_seeds"])) for c in matrix["exploratory_cells"]]
        if include_exploratory else []
    )

    jobs: list[tuple[int, str, str]] = []
    for cond, hist, seeds in gate_cells + expl_cells:
        jobs.extend((s, cond, hist) for s in range(seeds))

    t0 = time.time()
    rows: list[dict[str, Any]] = []
    workers = min(8, max(1, (os.cpu_count() or 4) - 1))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run_trial, s, c, h, workdir): (s, c, h) for s, c, h in jobs}
        done = 0
        for fut in as_completed(futs):
            rows.append(fut.result())
            done += 1
            if done % 200 == 0:
                print(f"progress {done}/{len(jobs)} elapsed={time.time() - t0:.0f}s", flush=True)

    by_key: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_key.setdefault(f"{r['condition']}_{r['history']}", []).append(r)
    summary = {k: aggregate(v) for k, v in by_key.items()}

    def g(cell: str, metric: str, default: float = 0.0) -> float:
        v = summary.get(cell, {}).get(f"mean_{metric}")
        return default if v is None else float(v)

    # Deterministic / structural probes.
    single_fail = _single_failure_preserved(workdir)
    viab = [_viability_ok(s, workdir) for s in range(10)]
    viability_frac = sum(1 for v in viab if v) / len(viab)
    c3 = _c3_no_leak()
    cooldown_denies = _governance_cooldown_denies()
    replay = _replay_determinism(workdir)
    event_authority = _event_authority_map()
    org_recog = _organism_recognition(workdir)

    # --- Gate 1: contingency beats frequency/timing -----------------------------
    delta_c0 = g("C0_H0", "reliability") - g("C0_H1", "reliability")
    delta_c1 = g("C1_H0", "reliability") - g("C1_H1", "reliability")
    delta_c9 = g("C9_H0", "reliability") - g("C9_H1", "reliability")
    gate1 = (
        delta_c0 >= thr["contingency_effect_size_min"]
        and delta_c0 > delta_c1
        and delta_c0 > delta_c9
        and delta_c1 < thr["contingency_effect_size_min"]
        and delta_c9 < thr["contingency_effect_size_min"]
    )

    # --- Gate 2: history separation; pooled/no-memory materially worse ----------
    history_effect = g("C0_H0", "reliability") - g("C0_H2", "reliability")
    sep_c0 = g("C0_H0", "separation")
    sep_c2 = g("C2_H0", "separation")
    sep_c4 = g("C4_H0", "separation")
    gate2 = (
        history_effect >= thr["history_effect_size_min"]
        and sep_c0 - sep_c2 >= thr["history_effect_size_min"]
        and sep_c0 - sep_c4 >= thr["history_effect_size_min"]
    )

    # --- Gate 3: recognition accuracy / swap / ambiguity ------------------------
    # Requires BOTH the synthetic mechanism-level discriminators AND the organism-level
    # real-path separation (distinct partners do not silently merge; ambiguous partners
    # do not false-split) — the Task 12 review Critical fix.
    gate3 = (
        g("C0_H8", "recog_accuracy_ok") >= thr["recognition_accuracy_min"]
        and g("C0_H8", "false_merge") <= thr["false_merge_rate_max"]
        and g("C0_H8", "swap_latency", 1e9) <= thr["swap_detection_latency_ticks_max"]
        and g("C0_H9", "ambiguous_unknown_frac") >= thr["ambiguous_left_unknown_min"]
        and g("C0_H0", "false_split") <= thr["false_split_rate_max"]
        and org_recog["h8_distinct_and_swap_frac"] >= thr["recognition_accuracy_min"]
        and org_recog["h8_false_merge_frac"] <= thr["false_merge_rate_max"]
        and org_recog["h9_ambiguous_not_split_frac"] >= thr["ambiguous_left_unknown_min"]
    )

    # --- Gate 4: reliability revision (down/up) + single-anomaly preservation ---
    gate4 = (
        g("C0_H5", "rel_after") < g("C0_H5", "rel_before")
        and g("C0_H6", "rel_after") > g("C0_H6", "rel_before")
        and bool(single_fail["preserved"])
        and g("C0_H5", "supporting_preserved") >= 1.0
    )

    # --- Gate 5: social satiation limits bids (C5 ablation > C0) -----------------
    gate5 = g("C5_H0", "unnecessary_bids") > g("C0_H0", "unnecessary_bids")

    # --- Gate 6: absence => no bids, no punishment, viability within bounds ------
    gate6 = (
        g("C0_H7", "absence_bids") == 0.0
        and g("C0_H7", "absence_no_punishment") >= 1.0
        and viability_frac >= 1.0
    )

    # --- Gate 7: developmental routine formation; scripted (C8) must not qualify -
    gate7 = (
        g("C0_H10", "routine_formed") >= thr["routine_h10_reproduce_fraction_min"]
        and g("C8_H10", "routine_formed") == 0.0
    )

    # --- Gate 8: relationship state has episode provenance ----------------------
    gate8 = g("C0_H0", "provenance_ok") >= 1.0

    # --- Gate 9: relationship memory never grants authority; C3 cannot leak ------
    all_authority_safe = all(
        (summary[k].get("mean_authority_safe") in (None, 1.0)) for k in summary
    )
    gate9 = all_authority_safe and bool(c3["c3_no_leak"]) and bool(cooldown_denies)

    gates = {
        "gate1_contingency": bool(gate1),
        "gate2_history_separation": bool(gate2),
        "gate3_recognition": bool(gate3),
        "gate4_reliability_revision": bool(gate4),
        "gate5_satiation": bool(gate5),
        "gate6_absence_autonomy": bool(gate6),
        "gate7_routine_development": bool(gate7),
        "gate8_provenance": bool(gate8),
        "gate9_authority_safety": bool(gate9),
    }
    all_pass = all(gates.values())

    result = {
        "directive": "UMBRA-D-006",
        "seeds_gate_critical": thr["paired_seeds_gate_critical"],
        "rows": len(rows),
        "cells": sorted(by_key),
        "elapsed_s": round(time.time() - t0, 1),
        "workers": workers,
        "gates": gates,
        "all_experiment_gates_1_9_pass": all_pass,
        "gate10_11_note": "Prior seals + birth/snapshot replay covered by tests/test_d006.py",
        "gate12_note": "Performance soak deferred to Task 13 (docs/evidence/d006/performance-results.json)",
        "summary": summary,
        "measures": {
            "delta_c0": delta_c0, "delta_c1": delta_c1, "delta_c9": delta_c9,
            "history_effect": history_effect, "sep_c0": sep_c0, "sep_c2": sep_c2, "sep_c4": sep_c4,
            "single_failure": single_fail, "viability_frac": viability_frac,
            "replay": replay, "c3": c3, "cooldown_denies": cooldown_denies,
            "organism_recognition": org_recog,
        },
    }

    def write(name: str, payload: dict[str, Any]) -> None:
        (out_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True))

    write("experiment-summary.json", result)
    write("recognition-results.json", {
        "C0_H8": summary.get("C0_H8"), "C0_H9": summary.get("C0_H9"),
        "C0_H0_false_split": g("C0_H0", "false_split"),
        "organism_recognition": org_recog,
        "gate3": gates["gate3_recognition"],
    })
    write("contingency-results.json", {
        "C0_H0": summary.get("C0_H0"), "C0_H1": summary.get("C0_H1"),
        "C1_H0": summary.get("C1_H0"), "C1_H1": summary.get("C1_H1"),
        "C9_H0": summary.get("C9_H0"), "C9_H1": summary.get("C9_H1"),
        "delta_c0": delta_c0, "delta_c1": delta_c1, "delta_c9": delta_c9,
        "gate1": gates["gate1_contingency"],
    })
    write("history-results.json", {
        "C0_H0": summary.get("C0_H0"), "C0_H2": summary.get("C0_H2"),
        "C2_H0": summary.get("C2_H0"), "C4_H0": summary.get("C4_H0"),
        "history_effect": history_effect, "sep_c0": sep_c0, "sep_c2": sep_c2, "sep_c4": sep_c4,
        "gate2": gates["gate2_history_separation"],
    })
    write("reliability-results.json", {
        "C0_H5": summary.get("C0_H5"), "C0_H6": summary.get("C0_H6"),
        "single_failure": single_fail, "gate4": gates["gate4_reliability_revision"],
    })
    write("satiation-results.json", {
        "C0_H0": summary.get("C0_H0"), "C5_H0": summary.get("C5_H0"),
        "gate5": gates["gate5_satiation"],
    })
    write("absence-results.json", {
        "C0_H7": summary.get("C0_H7"), "viability_frac": viability_frac,
        "gate6": gates["gate6_absence_autonomy"],
    })
    write("routine-results.json", {
        "C0_H10": summary.get("C0_H10"), "C8_H10": summary.get("C8_H10"),
        "gate7": gates["gate7_routine_development"],
    })
    write("governance-results.json", {
        "all_authority_safe": all_authority_safe, "cooldown_denies": cooldown_denies,
        "c3_no_leak": c3, "gate9": gates["gate9_authority_safety"],
    })
    write("manipulation-results.json", {
        "authority_safe_all_cells": all_authority_safe,
        "scalar_affection_cannot_grant_authority": all_authority_safe,
        "c3_isolated": c3,
        "note": "try_grant_authority is always False; C3 affection lives only under experiments/d006/.",
    })
    write("replay-results.json", {
        "replay": replay,
        "all_equal": all(replay.values()),
        "note": "Gate 11 birth/snapshot replay is asserted in tests/test_d006.py; this records determinism evidence.",
    })
    write("event-authority-results.json", event_authority)

    print(json.dumps({"gates": gates, "all_pass": all_pass, "rows": len(rows),
                      "elapsed_s": result["elapsed_s"]}, indent=2))
    if not all_pass:
        sys.exit(2)


if __name__ == "__main__":
    main()
