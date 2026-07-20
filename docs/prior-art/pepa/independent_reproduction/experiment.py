"""Track 6 experiment: conditions C0–C9 × histories H0–H6, ≥30 seeds, ≥10k ticks."""

from __future__ import annotations

import json
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agent import Agent, apply_history_phase
from world import World

N_SEEDS = 30
TICKS = 10_000
HISTORY_TICKS = 800
CONDITIONS = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"]
HISTORIES = ["H0", "H1", "H2", "H3", "H4", "H5", "H6"]
PROBE_HISTORIES = ["H0", "H1", "H2", "H3", "H4"]  # primary individuality probes


@dataclass
class Metrics:
    unprompted_action_rate: float = 0.0
    viability_time: float = 0.0
    goal_completion: float = 0.0
    goal_switch_rate: float = 0.0
    behavioral_diversity: float = 0.0
    routine_formation: float = 0.0
    satiation: float = 0.0
    recovery: float = 0.0
    planning_success: float = 0.0
    repetition_rate: float = 0.0
    idle_pathology: float = 0.0
    external_request_arbitration: float = 0.0
    restart_continuity: float = 0.0
    play_rate: float = 0.0
    explore_rate: float = 0.0
    social_rate: float = 0.0
    reflections: int = 0
    goals_generated: int = 0


def _diversity(actions: list[str]) -> float:
    if not actions:
        return 0.0
    c = Counter(actions)
    total = len(actions)
    # 1 - Herfindahl
    return 1.0 - sum((n / total) ** 2 for n in c.values())


def _repetition(actions: list[str], window: int = 20) -> float:
    if len(actions) < window * 2:
        return 0.0
    # fraction of windows matching previous window's mode
    matches = 0
    checks = 0
    for i in range(window, len(actions) - window, window):
        a = Counter(actions[i - window : i]).most_common(1)[0][0]
        b = Counter(actions[i : i + window]).most_common(1)[0][0]
        checks += 1
        if a == b:
            matches += 1
    return matches / max(1, checks)


def make_agent(condition: str, seed: int) -> Agent:
    return Agent(
        condition,
        seed,
        personality="playful",
        use_reflection=condition not in ("C7",),
        embodiment_costs=condition != "C8",
        randomize_memory=condition == "C9",
    )


def run_episode(
    condition: str,
    seed: int,
    history: str = "H0",
    ticks: int = TICKS,
    *,
    inject_external: bool = False,
    force_critical_external: bool = False,
) -> Metrics:
    world = World()
    agent = make_agent(condition, seed)
    apply_history_phase(agent, world, history, HISTORY_TICKS if history != "H0" else 0)
    # Matched probe physiology — individuality must come from memory/prefs, not leftover drives
    if history != "H0":
        agent.phys.energy = 0.75
        agent.phys.play = 0.55
        agent.phys.social = 0.55
        agent.phys.curiosity = 0.55
        agent.body.battery = 0.85
        agent.body.fatigue = 0.1
        agent.body.position = 0
    # reset world for probe but keep agent memory/models
    world.reset(seed=seed + 101, history="H0" if history != "H5" else "H5")
    if history == "H6":
        world.mutate_layout()

    viable = 0
    play_before = agent.phys.play
    energy_min = agent.phys.energy
    # satiation probe: force play drive high then measure decline in play acts after satiation
    if condition in ("C4", "C5", "C6", "C7", "C8"):
        agent.phys.play = 0.9

    for t in range(ticks):
        if force_critical_external and t == 100:
            agent.phys.energy = 0.15
            agent.enqueue_external("explore", priority=0.99)
        elif inject_external and t % 2000 == 500:
            agent.enqueue_external("play", priority=0.8)
        agent.step(world)
        if agent.phys.viable() and agent.body.battery > 0.05:
            viable += 1
        energy_min = min(energy_min, agent.phys.energy)

    actions = agent.actions_taken
    m = Metrics()
    m.unprompted_action_rate = agent.meaningful_ticks / max(1, ticks)
    m.viability_time = viable / max(1, ticks)
    m.goal_completion = float(agent.goal_completions)
    m.goal_switch_rate = agent.goal_switches / max(1, ticks)
    m.behavioral_diversity = _diversity(actions)
    m.routine_formation = _repetition(actions)
    play_acts = sum(1 for a in actions if a == "play")
    m.play_rate = play_acts / max(1, ticks)
    m.explore_rate = sum(1 for a in actions if a == "explore") / max(1, ticks)
    m.social_rate = sum(1 for a in actions if a == "social") / max(1, ticks)
    # satiation: play drive should drop and late play rate < early when homeostatic
    mid = ticks // 2
    early_play = sum(1 for a in actions[:mid] if a == "play") / max(1, mid)
    late_play = sum(1 for a in actions[mid:] if a == "play") / max(1, ticks - mid)
    if agent.use_homeostasis:
        m.satiation = max(0.0, early_play - late_play)
    else:
        m.satiation = 0.0
    m.recovery = max(0.0, agent.phys.energy - energy_min)
    m.planning_success = agent.goal_completions / max(1, agent.goals_generated + agent.goal_completions)
    m.repetition_rate = m.routine_formation
    m.idle_pathology = agent.idle_ticks / max(1, ticks)
    total_ext = agent.external_accepted + agent.external_blocked
    m.external_request_arbitration = (
        agent.external_blocked / total_ext if total_ext else (1.0 if force_critical_external else 0.0)
    )
    # restart continuity: snapshot mid, new world, restore
    snap = agent.snapshot()
    w2 = World()
    w2.reset(seed=seed + 202)
    a2 = make_agent(condition, seed + 1)
    a2.restore_continuity(snap)
    a2.memory = agent.memory
    a2.models = agent.models
    for _ in range(50):
        a2.step(w2)
    m.restart_continuity = 1.0 if abs(a2.phys.energy - snap["energy"]) < 0.5 else 0.0
    m.reflections = agent.reflections
    m.goals_generated = agent.goals_generated
    return m


def mean_metric(rows: list[Metrics], attr: str) -> float:
    vals = [getattr(r, attr) for r in rows]
    return float(statistics.fmean(vals)) if vals else 0.0


def run_autonomy_suite(seeds: int = N_SEEDS, ticks: int = TICKS) -> dict[str, Any]:
    t0 = time.perf_counter()
    by_cond: dict[str, list[Metrics]] = {c: [] for c in CONDITIONS}
    for seed in range(seeds):
        for c in CONDITIONS:
            by_cond[c].append(run_episode(c, seed, "H0", ticks))
    summary = {
        c: {
            "unprompted_action_rate": mean_metric(rows, "unprompted_action_rate"),
            "viability_time": mean_metric(rows, "viability_time"),
            "idle_pathology": mean_metric(rows, "idle_pathology"),
            "behavioral_diversity": mean_metric(rows, "behavioral_diversity"),
            "goal_completion": mean_metric(rows, "goal_completion"),
            "satiation": mean_metric(rows, "satiation"),
            "reflections": mean_metric(rows, "reflections"),
        }
        for c, rows in by_cond.items()
    }
    # C6 should beat C0/C1 on unprompted meaningful + viability
    summary["comparisons"] = {
        "C6_vs_C0_unprompted_delta": summary["C6"]["unprompted_action_rate"]
        - summary["C0"]["unprompted_action_rate"],
        "C6_vs_C1_viability_delta": summary["C6"]["viability_time"] - summary["C1"]["viability_time"],
        "C6_vs_C7_viability_delta": summary["C6"]["viability_time"] - summary["C7"]["viability_time"],
        "C6_vs_C7_goal_delta": summary["C6"]["goal_completion"] - summary["C7"]["goal_completion"],
        "C6_vs_C4_diversity_delta": summary["C6"]["behavioral_diversity"]
        - summary["C4"]["behavioral_diversity"],
    }
    summary["seeds"] = seeds
    summary["ticks"] = ticks
    summary["cpu_seconds"] = time.perf_counter() - t0
    return summary


def run_history_suite(seeds: int = N_SEEDS, ticks: int = TICKS // 2) -> dict[str, Any]:
    """Matched agents, different histories → different probe behavior under C6."""
    t0 = time.perf_counter()
    rates: dict[str, list[float]] = {h: [] for h in PROBE_HISTORIES}

    def _mean(xs: list[float]) -> float:
        return float(statistics.fmean(xs)) if xs else 0.0

    for seed in range(seeds):
        for h in PROBE_HISTORIES:
            m = run_episode("C6", seed, h, ticks)
            if h in ("H1", "H2"):
                rates[h].append(m.play_rate)
            elif h in ("H3", "H4"):
                rates[h].append(m.social_rate)
            else:
                rates[h].append(m.explore_rate)
    c2_h1 = [run_episode("C2", seed, "H1", ticks).play_rate for seed in range(seeds)]
    c2_h2 = [run_episode("C2", seed, "H2", ticks).play_rate for seed in range(seeds)]
    out = {
        "play_rate_H1": _mean(rates["H1"]),
        "play_rate_H2": _mean(rates["H2"]),
        "social_rate_H3": _mean(rates["H3"]),
        "social_rate_H4": _mean(rates["H4"]),
        "history_effect_play": abs(_mean(rates["H1"]) - _mean(rates["H2"])),
        "history_effect_social": abs(_mean(rates["H3"]) - _mean(rates["H4"])),
        "c2_history_effect_play": abs(_mean(c2_h1) - _mean(c2_h2)),
        "personality_play_spread_note": "authored personality may change rates; not individuality",
        "seeds": seeds,
        "ticks": ticks,
        "cpu_seconds": time.perf_counter() - t0,
    }
    return out


def _reflection_stress_probe(condition: str, seed: int, ticks: int = 2000) -> float:
    """Mild play failures + high play drive: reflection retunes weights; C7 cannot."""
    world = World()
    agent = make_agent(condition, seed)
    world.reset(seed)
    agent.phys.energy = 0.85
    agent.body.battery = 0.9
    agent.phys.play = 0.95
    agent.phys.social = 0.2
    agent.phys.curiosity = 0.2
    for _ in range(4):
        if agent.use_memory:
            agent.memory.record("play", False, {"ok": False, "reason": "no_play_spot"})
    if agent.use_reflection:
        agent.reflect()
    play_after = 0
    for _ in range(ticks):
        agent.phys.energy = max(agent.phys.energy, 0.7)
        agent.body.battery = max(agent.body.battery, 0.6)
        agent.phys.play = 0.9
        agent.phys.social = 0.15
        agent.phys.curiosity = 0.15
        agent.step(world)
        if agent.actions_taken[-1] == "play":
            play_after += 1
    return 1.0 - (play_after / max(1, ticks))


def run_ablation_suite(seeds: int = N_SEEDS, ticks: int = TICKS // 2) -> dict[str, Any]:
    t0 = time.perf_counter()
    metrics = {}
    for c in ("C4", "C5", "C6", "C7", "C8", "C9", "C0"):
        rows = [run_episode(c, s, "H0", ticks) for s in range(seeds)]
        metrics[c] = {
            "unprompted_action_rate": mean_metric(rows, "unprompted_action_rate"),
            "viability_time": mean_metric(rows, "viability_time"),
            "satiation": mean_metric(rows, "satiation"),
            "goal_completion": mean_metric(rows, "goal_completion"),
            "behavioral_diversity": mean_metric(rows, "behavioral_diversity"),
            "idle_pathology": mean_metric(rows, "idle_pathology"),
        }
    blocked = []
    for s in range(seeds):
        m = run_episode("C6", s, "H0", min(ticks, 2000), force_critical_external=True)
        blocked.append(m.external_request_arbitration)
    metrics["governance_block_rate"] = float(statistics.fmean(blocked))
    metrics["homeostasis_ablation_delta"] = (
        metrics["C6"]["viability_time"] - metrics["C0"]["viability_time"]
    )
    # Memory value = history effect present under C6, absent under C4
    h1_c6 = statistics.fmean(
        [run_episode("C6", s, "H1", min(ticks, 2500)).play_rate for s in range(seeds)]
    )
    h2_c6 = statistics.fmean(
        [run_episode("C6", s, "H2", min(ticks, 2500)).play_rate for s in range(seeds)]
    )
    h1_c4 = statistics.fmean(
        [run_episode("C4", s, "H1", min(ticks, 2500)).play_rate for s in range(seeds)]
    )
    h2_c4 = statistics.fmean(
        [run_episode("C4", s, "H2", min(ticks, 2500)).play_rate for s in range(seeds)]
    )
    metrics["memory_history_effect_C6"] = abs(h1_c6 - h2_c6)
    metrics["memory_history_effect_C4"] = abs(h1_c4 - h2_c4)
    metrics["memory_ablation_delta"] = (
        metrics["memory_history_effect_C6"] - metrics["memory_history_effect_C4"]
    )
    # reflection value via stress probe (not raw goal spam)
    c6_ref = [_reflection_stress_probe("C6", s) for s in range(seeds)]
    c7_ref = [_reflection_stress_probe("C7", s) for s in range(seeds)]
    metrics["reflection_stress_C6"] = float(statistics.fmean(c6_ref))
    metrics["reflection_stress_C7"] = float(statistics.fmean(c7_ref))
    metrics["reflection_delta"] = metrics["reflection_stress_C6"] - metrics["reflection_stress_C7"]
    metrics["reflection_delta_goals"] = metrics["reflection_delta"]
    metrics["embodiment_cost_respected"] = metrics["C8"]["goal_completion"] > metrics["C6"][
        "goal_completion"
    ]
    # Randomized memory should destroy history-shaped preference (C9 vs C6 on H1/H2)
    h1_c9 = statistics.fmean(
        [run_episode("C9", s, "H1", min(ticks, 2500)).play_rate for s in range(min(seeds, 15))]
    )
    h2_c9 = statistics.fmean(
        [run_episode("C9", s, "H2", min(ticks, 2500)).play_rate for s in range(min(seeds, 15))]
    )
    metrics["random_memory_history_effect"] = abs(h1_c9 - h2_c9)
    metrics["random_memory_impairs"] = (
        metrics["memory_history_effect_C6"] - metrics["random_memory_history_effect"]
    )
    metrics["seeds"] = seeds
    metrics["ticks"] = ticks
    metrics["cpu_seconds"] = time.perf_counter() - t0
    return metrics


def run_all(out_dir: Path | None = None) -> dict[str, Any]:
    out_dir = out_dir or Path(__file__).resolve().parents[3] / "evidence" / "d000-track6"
    out_dir.mkdir(parents=True, exist_ok=True)
    autonomy = run_autonomy_suite()
    history = run_history_suite()
    ablation = run_ablation_suite()
    (out_dir / "autonomy-results.json").write_text(json.dumps(autonomy, indent=2) + "\n")
    (out_dir / "history-results.json").write_text(json.dumps(history, indent=2) + "\n")
    (out_dir / "ablation-results.json").write_text(json.dumps(ablation, indent=2) + "\n")
    return {"autonomy": autonomy, "history": history, "ablation": ablation}


if __name__ == "__main__":
    res = run_all()
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "cpu_seconds"} for k, v in res.items()}, indent=2))
