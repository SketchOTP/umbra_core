"""AS-015-owned downstream qualification surfaces.

The quantitative contracts are inherited from AS-014, but every organism is
constructed through the AS-015 full-configuration factory.  The fifth
ablation disables only the explicit viability-kernel switch; terminal
executability and verified branch safety remain active.
"""

from __future__ import annotations

import contextlib
import copy
from pathlib import Path
from typing import Any, Iterator

from experiments.as009.qualification import partner_object
from experiments.as014 import downstream as _as014
from experiments.as014.full_config import LEDGER_CONTRACT
from experiments.as015.full_config import BASELINE, DIRECTIVE, config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism, restore_habitat_engine_from_checkpoint


ACCELERATED = dict(_as014.ACCELERATED)
SOAK = dict(_as014.SOAK)
VARIANTS = (
    "FULL",
    "TERMINAL_READINESS_DISABLED",
    "CONTINUATION_DISABLED",
    "ROUTE_LEARNING_DISABLED",
    "VIABILITY_KERNEL_DISABLED",
)


@contextlib.contextmanager
def _as015_config_scope() -> Iterator[None]:
    """Reuse AS-014 measurement mechanics, never its config authority."""
    original = (_as014.config, _as014.fingerprint, _as014.DIRECTIVE, _as014.BASELINE)
    _as014.config, _as014.fingerprint = config, fingerprint
    _as014.DIRECTIVE, _as014.BASELINE = DIRECTIVE, BASELINE
    try:
        yield
    finally:
        _as014.config, _as014.fingerprint, _as014.DIRECTIVE, _as014.BASELINE = original


def _decorate(result: dict[str, Any], schema: str, *, viability_kernel: bool = True) -> dict[str, Any]:
    result = dict(result)
    result.update(
        schema=schema,
        directive=DIRECTIVE,
        baseline=BASELINE,
        viability_kernel_enabled=viability_kernel,
        canonical_configuration="AS015_FULL_CONFIGURATION",
    )
    return result


def boundedness(
    seed: int,
    work: Path,
    ticks: int = ACCELERATED["ticks"],
    *,
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with _as015_config_scope():
        result = _as014.boundedness(seed, work, ticks, ledger_overrides=ledger_overrides)
    return _decorate(result, "AS015_BOUNDEDNESS_RESULT_V1")


def soak(
    seed: int,
    work: Path,
    *,
    warmup_seconds: float = SOAK["warmup_seconds"],
    measure_seconds: float = SOAK["measure_seconds"],
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with _as015_config_scope():
        result = _as014.soak(
            seed,
            work,
            warmup_seconds=warmup_seconds,
            measure_seconds=measure_seconds,
            ledger_overrides=ledger_overrides,
        )
    return _decorate(result, "AS015_REALTIME_SOAK_RESULT_V1")


def _initialize(seed: int, db: Path, *, ledger_overrides: dict[str, Any] | None = None):
    organism = create_organism(config(seed, db, "R0", ledger_overrides=ledger_overrides))
    _as014._ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario("S10"))
    organism.embodiment.attach_habitat_engine(engine)
    return organism, engine


def _restore(seed: int, db: Path, *, ledger_overrides: dict[str, Any] | None = None):
    organism = load_organism(config(seed, db, "R0", ledger_overrides=ledger_overrides))
    engine = restore_habitat_engine_from_checkpoint(organism)
    binding = organism.embodiment.habitat_authority_binding
    view = engine.snapshot_view()
    if binding is None or binding["habitat_id"] != view.habitat_id or binding["state_hash"] != view.state_hash:
        raise RuntimeError("AS015_HABITAT_REATTACHMENT_INVALID")
    return organism, engine


def _finalize_restart(
    organism: Any,
    engine: HabitatEngine,
    seed: int,
    db: Path,
    regime: str,
    *,
    continuation: bool = True,
    route_learning: bool = True,
    viability_kernel: bool = True,
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if organism.embodiment._habitat_engine is not engine:
        raise RuntimeError("AS015_FINALIZATION_ENGINE_MISMATCH")
    before = organism.authoritative_state()
    snapshot_id = organism.snapshot_if_due(force=True)
    organism.store.validate_chain()
    organism.close()
    restored = load_organism(
        config(
            seed,
            db,
            regime,
            bounded_continuation=continuation,
            route_learning=route_learning,
            viability_kernel=viability_kernel,
            ledger_overrides=ledger_overrides,
        )
    )
    restored_engine = restore_habitat_engine_from_checkpoint(restored)
    after = restored.authoritative_state()
    restored.store.validate_chain()
    result = {
        "snapshot_id": snapshot_id,
        "restart_continuity": after["identity"] == before["identity"] and after["tick"] == before["tick"],
        "restart_habitat_state_hash": restored_engine.snapshot_view().state_hash,
        "final_hot_tail_events": len(restored.store.iter_events()),
        "final_checkpoint_count": int(restored.store.conn.execute("SELECT COUNT(*) FROM ledger_checkpoints").fetchone()[0]),
        "final_snapshot_count": int(restored.store.conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]),
        "final_event_sequence": restored.store.last_sequence(),
    }
    restored.close()
    return result


def lifecycle(
    seed: int,
    work: Path,
    *,
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Exercise persistence maintenance, restart, replacement, and profile swap."""
    db = work / "lifecycle.sqlite"
    organism, engine = _initialize(seed, db, ledger_overrides=ledger_overrides)
    identity = organism.identity.as_dict()
    engine.commit_object_creation(
        partner_object(),
        event_id=f"as015:lifecycle:create:{seed}",
        transaction_id=f"as015:lifecycle:create-txn:{seed}",
        request_id=f"as015:lifecycle:create-req:{seed}",
    )
    checkpoint_epochs: list[int] = []
    try:
        for _ in range(3):
            organism.run_ticks(160)
            organism.snapshot_if_due(force=True)
            checkpoint = organism.store.latest_checkpoint()
            checkpoint_epochs.append(int(checkpoint["checkpoint_epoch"]) if checkpoint else 0)
            organism.close()
            organism, engine = _restore(seed, db, ledger_overrides=ledger_overrides)
        pre_replace_identity = organism.identity.as_dict() == identity
        old_body = organism.embodiment_adapter.state.body_instance_id
        owner_state = (
            organism.memory.to_state(),
            organism.social.to_state(),
            organism.individuality.to_state(),
        )
        replacement = organism.replace_physical_body(
            new_profile_id="MINIMAL_CREATURE_BODY", reason="as015_lifecycle"
        )
        replacement_ok = (
            replacement["new_body_instance_id"] != old_body
            and organism.embodiment.body_occupancy_view().body_instance_id
            == replacement["new_body_instance_id"]
            and organism.self_model.body_binding_id == replacement["new_body_binding_id"]
            and owner_state
            == (organism.memory.to_state(), organism.social.to_state(), organism.individuality.to_state())
        )
        organism.snapshot_if_due(force=True)
        organism.close()
        organism, engine = _restore(seed, db, ledger_overrides=ledger_overrides)
        post_replacement_restart = (
            organism.identity.as_dict() == identity
            and organism.embodiment_adapter.state.body_instance_id
            == replacement["new_body_instance_id"]
        )
        organism.embodiment_adapter.swap_profile(
            "ABSTRACT_SHAPE_BODY", origin="AS015_LIFECYCLE_PROFILE_SWAP"
        )
        profile_ok = (
            organism.embodiment_adapter.state.body_instance_id
            == replacement["new_body_instance_id"]
            and organism.embodiment.body_occupancy_view().body_instance_id
            == replacement["new_body_instance_id"]
        )
        organism.run_ticks(80)
        organism.store.validate_chain()
        result = {
            "schema": "AS015_LIFECYCLE_RESULT_V1",
            "directive": DIRECTIVE,
            "baseline": BASELINE,
            "seed": seed,
            "checkpoint_epochs": checkpoint_epochs,
            "checks": {
                "restart_identity_and_habitat": pre_replace_identity,
                "multiple_checkpoint_cycles": max(checkpoint_epochs, default=0) >= 2,
                "true_body_replacement": replacement_ok,
                "post_replacement_restart": post_replacement_restart,
                "compatible_profile_swap": profile_ok,
                "continued_after_replacement": organism.tick >= 560,
            },
            "ticks": organism.tick,
            "viability_kernel_state": "stateless_derivation_from_current_authority_sources",
            "configuration": fingerprint(organism.config),
        }
        result["pass"] = all(result["checks"].values())
        return result
    finally:
        organism.close()


def ablation(
    seed: int,
    work: Path,
    variant: str,
    ticks: int = 7200,
    *,
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise ValueError(variant)
    if variant != "VIABILITY_KERNEL_DISABLED":
        with _as015_config_scope():
            result = _as014.ablation(seed, work, variant, ticks, ledger_overrides=ledger_overrides)
        return _decorate(result, "AS015_ABLATION_RESULT_V1")

    db = work / "viability_kernel_disabled.sqlite"
    organism = create_organism(
        config(seed, db, "R1", viability_kernel=False, ledger_overrides=ledger_overrides)
    )
    _as014._ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario("S16"))
    organism.embodiment.attach_habitat_engine(engine)
    actions: list[str] = []
    first_no_safe: int | None = None
    try:
        for _ in range(ticks):
            decision = organism.tick_once()
            actions.append(str(decision.get("capability")))
            if decision.get("no_safe_action") and first_no_safe is None:
                first_no_safe = organism.tick
        final = _finalize_restart(
            organism,
            engine,
            seed,
            db,
            "R1",
            viability_kernel=False,
            ledger_overrides=ledger_overrides,
        )
        result = {
            "schema": "AS015_ABLATION_RESULT_V1",
            "directive": DIRECTIVE,
            "baseline": BASELINE,
            "variant": variant,
            "seed": seed,
            "ticks": ticks,
            "viability_kernel_enabled": False,
            "configuration": fingerprint(config(seed, db, "R1", viability_kernel=False, ledger_overrides=ledger_overrides)),
            "action_counts": {name: actions.count(name) for name in sorted(set(actions))},
            "first_no_safe_action": first_no_safe,
            "kernel_seam": {"disabled": True, "verified_branch_safety_retained": True, "terminal_executability_retained": True},
            **final,
        }
        result["pass"] = bool(ticks == 7200 and result["restart_continuity"])
        return result
    finally:
        # `_finalize_restart` closes the live organism.  On an early error,
        # `close` remains idempotent for the experiment fixture.
        organism.close()


__all__ = ["ACCELERATED", "SOAK", "VARIANTS", "ablation", "boundedness", "lifecycle", "soak"]
