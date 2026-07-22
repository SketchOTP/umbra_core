"""History evidence schedules for D-007 gate experiments.

Produces verified-evidence sequences that alter consequences — never
commands internal personality state. Used by run_experiment.py.
"""

from __future__ import annotations

from umbra_core.individuality import VerifiedEvidence
from umbra_core.util import SeededRNG


def evidence_schedule(
    history: str, *, seed: int, n_events: int = 48, shuffle: bool = False
) -> list[VerifiedEvidence]:
    """Return verified evidence for a preregistered history code."""
    rng = SeededRNG(seed + 17)
    items: list[VerifiedEvidence] = []

    def add(i: int, dim: str, scope: str, signed: float, **kw) -> None:
        items.append(
            VerifiedEvidence(
                evidence_id=f"ev-{seed}-{i}-{dim}-{scope[:4]}",
                tick=i + 1,
                source_system=kw.get("source_system", "outcome"),
                dimension=dim,
                context_scope=scope,
                signed_outcome=signed,
                verified=True,
                executed=True,
                from_episode=kw.get("from_episode", True),
                from_procedural=kw.get("from_procedural", False),
                from_frequency_only=kw.get("from_frequency_only", False),
                is_anomaly=kw.get("is_anomaly", False),
                severe_safety=kw.get("severe_safety", False),
                action=kw.get("action"),
            )
        )

    if history == "H0":
        for i in range(n_events):
            # Balanced mild mixed outcomes — stays near neutral
            dim = [
                "exploration_tendency",
                "novelty_tolerance",
                "persistence_after_failure",
                "uncertainty_caution",
            ][i % 4]
            scope = ["safe_explore", "novelty_probe", "solvable_task", "uncertain_hazard"][i % 4]
            add(i, dim, scope, rng.uniform(-0.15, 0.15))
    elif history == "H1":
        for i in range(n_events):
            add(i, "exploration_tendency", "safe_explore", 0.85, action="MOVE")
            if i % 2 == 0:
                add(i, "novelty_tolerance", "novelty_probe", 0.75, action="INSPECT")
    elif history == "H2":
        for i in range(n_events):
            add(i, "exploration_tendency", "uncertain_hazard", -0.85, action="MOVE")
            add(i, "uncertainty_caution", "uncertain_hazard", 0.9, action="RETREAT")
            add(i, "novelty_tolerance", "novelty_probe", -0.7, action="INSPECT")
    elif history == "H3":
        for i in range(n_events):
            add(i, "persistence_after_failure", "solvable_task", 0.9, action="INSPECT")
            if i % 3 == 0:
                add(
                    i,
                    "persistence_after_failure",
                    "practice",
                    0.7,
                    action="CHARGE",
                    from_procedural=True,
                    source_system="development",
                )
    elif history == "H4":
        for i in range(n_events):
            add(i, "persistence_after_failure", "solvable_task", -0.85, action="INSPECT")
    elif history == "H5":
        for i in range(n_events):
            add(i, "stimulation_tolerance", "high_stim", 0.9, action="INSPECT")
    elif history == "H6":
        for i in range(n_events):
            add(i, "stimulation_tolerance", "high_stim", -0.85, action="INSPECT")
            add(i, "recovery_pacing", "post_stim_recovery", 0.9, action="REST")
    elif history == "H7":
        for i in range(n_events):
            add(i, "novelty_tolerance", "object_family_a", 0.9, action="INSPECT")
            add(i, "persistence_after_failure", "object_family_a", 0.8, action="APPROACH")
            if i % 4 == 0:
                add(
                    i,
                    "persistence_after_failure",
                    "object_family_a",
                    0.7,
                    from_procedural=True,
                    source_system="memory",
                )
    elif history == "H8":
        for i in range(n_events):
            add(i, "novelty_tolerance", "object_family_b", 0.9, action="INSPECT")
            add(i, "persistence_after_failure", "object_family_b", 0.8, action="APPROACH")
    elif history == "H9":
        for i in range(n_events):
            add(
                i,
                "social_initiative_by_context",
                "play_context",
                0.9,
                action="SIGNAL_PLAY",
                source_system="social",
            )
            if i % 2 == 0:
                add(
                    i,
                    "social_initiative_by_context",
                    "assistance_context",
                    0.75,
                    action="SIGNAL_ASSISTANCE",
                    source_system="social",
                )
    elif history == "H10":
        for i in range(n_events):
            add(
                i,
                "social_initiative_by_context",
                "play_context",
                -0.85,
                action="SIGNAL_PLAY",
                source_system="social",
            )
            add(
                i,
                "social_initiative_by_context",
                "assistance_context",
                -0.8,
                action="SIGNAL_ASSISTANCE",
                source_system="social",
            )
    elif history == "H11":
        for i in range(n_events):
            add(i, "activity_timing_preference", "routine_window", 0.85, action="MOVE")
            add(i, "activity_timing_preference", "diurnal_phase", 0.7, action="CHARGE")
    elif history == "H12":
        half = n_events // 2
        for i in range(half):
            add(i, "exploration_tendency", "safe_explore", 0.85, action="MOVE")
            add(i, "novelty_tolerance", "novelty_probe", 0.8, action="INSPECT")
        for i in range(half, n_events):
            add(i, "exploration_tendency", "safe_explore", -0.85, action="MOVE")
            add(i, "novelty_tolerance", "novelty_probe", -0.8, action="INSPECT")
    else:
        raise ValueError(f"unknown_history:{history}")

    if shuffle:
        rng.shuffle(items)
        # Re-assign evidence ids so shuffle is visible but still verified
        for j, ev in enumerate(items):
            ev.evidence_id = f"shuf-{seed}-{j}"
            ev.tick = j + 1
    return items
