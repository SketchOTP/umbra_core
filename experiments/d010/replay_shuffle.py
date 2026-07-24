"""D-010 C12 — shuffle temporal replay event order for ablation harnesses."""

from __future__ import annotations

from typing import Any, Sequence


def shuffle_replay_events(
    events: Sequence[dict[str, Any]],
    *,
    seed: int,
) -> list[dict[str, Any]]:
    """Return a permuted copy of replay events — experiments only."""
    from umbra_core.util import SeededRNG

    rng = SeededRNG(seed)
    out = list(events)
    rng.shuffle(out)
    return out
