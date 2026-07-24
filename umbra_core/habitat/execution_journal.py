"""D-009 MANIPULATE execution journal — PREPARED → COMMITTED_* exactly-once commits."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Callable

from umbra_core.governance import Governance, VerifiedOutcome
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.events import (
    HABITAT_AFFORDANCE_ACTIVATED,
    HABITAT_AFFORDANCE_DEACTIVATED,
    HABITAT_OBJECT_MOVED,
    HABITAT_OBJECT_PICKED_UP,
    HABITAT_OBJECT_PLACED,
    HABITAT_OBJECT_STATE_CHANGED,
    HabitatEventError,
    apply_habitat_event,
    build_habitat_event,
    build_object_moved_event,
    build_object_picked_up_event,
    build_object_placed_event,
)
from umbra_core.habitat.events import _location_from_payload, _object_state_from_payload
from umbra_core.habitat.state import (
    ActivatableState,
    FreeLocation,
    HabitatObject,
    HabitatState,
    HeldByLocation,
    MutationRejected,
    ResourceState,
    apply_committed_object_mutation,
    with_state_hash,
)
from umbra_core.habitat_affordances.engine import (
    AffordanceValidationResult,
    HabitatEffectPlan,
    ManipulationRequest,
)
from umbra_core.habitat_affordances.engine import _apply_world_effect_mutations
from umbra_core.persistence import PersistenceError, Store
from umbra_core.physiology import Physiology
from umbra_core.util import canon_json, new_id, sha256_hex

STATUS_PREPARED = "PREPARED"
STATUS_COMMITTED_SUCCESS = "COMMITTED_SUCCESS"
STATUS_COMMITTED_FAILURE = "COMMITTED_FAILURE"

EXECUTION_PAYLOAD_MISMATCH = "EXECUTION_PAYLOAD_MISMATCH"
HABITAT_COLLECTION_CAP_EXCEEDED = "HABITAT_COLLECTION_CAP_EXCEEDED"
EVENT_STORAGE_BUDGET_EXCEEDED = "EVENT_STORAGE_BUDGET_EXCEEDED"


class ExecutionJournalError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class PreparedExecution:
    execution_id: str
    request_id: str
    status: str
    canonical_payload_hash: str
    transaction_id: str
    prepared_tick: int
    outcome_id: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True)
class ManipulationCommitResult:
    execution_id: str
    request_id: str
    journal_status: str
    outcome: VerifiedOutcome | None
    failure_code: str | None
    idempotent_replay: bool = False


def canonical_payload_hash(request: ManipulationRequest) -> str:
    payload = {
        "request_id": request.request_id,
        "execution_id": request.execution_id,
        "capability": request.capability,
        "target_object_id": request.target_object_id,
        "affordance_id": request.affordance_id,
        "expected_habitat_version": request.expected_habitat_version,
        "expected_habitat_state_hash": request.expected_habitat_state_hash,
        "target_object_version": request.target_object_version,
        "target_object_definition_version": request.target_object_definition_version,
        "target_object_definition_hash": request.target_object_definition_hash,
        "affordance_definition_version": request.affordance_definition_version,
        "affordance_definition_hash": request.affordance_definition_hash,
        "body_instance_id": request.body_instance_id,
        "body_profile_id": request.body_profile_id,
        "attachment_generation": request.attachment_generation,
        "parameters": asdict(request.parameters),
    }
    return sha256_hex(canon_json(payload))


def organism_effects_to_physiology(effects: tuple[dict[str, Any], ...]) -> dict[str, float]:
    out: dict[str, float] = {}
    for effect in effects:
        kind = str(effect.get("effect_kind", ""))
        magnitude = float(effect.get("magnitude", 0.0))
        if kind == "RESOURCE_YIELD":
            out["energy"] = out.get("energy", 0.0) + magnitude
    return out


def prepare_execution(
    store: Store,
    request: ManipulationRequest,
    *,
    prepared_tick: int,
    transaction_id: str | None = None,
) -> PreparedExecution:
    payload_hash = canonical_payload_hash(request)
    existing = store.get_habitat_execution_journal(request.execution_id)
    if existing is not None:
        if existing["canonical_payload_hash"] != payload_hash:
            raise ExecutionJournalError(EXECUTION_PAYLOAD_MISMATCH)
        if existing["status"] != STATUS_PREPARED:
            raise ExecutionJournalError("execution_already_terminal")
        return _prepared_from_row(existing)

    by_request = store.get_habitat_execution_journal_by_request_id(request.request_id)
    if by_request is not None and by_request["canonical_payload_hash"] != payload_hash:
        raise ExecutionJournalError(EXECUTION_PAYLOAD_MISMATCH)
    if by_request is not None and by_request["status"] == STATUS_PREPARED:
        if by_request["execution_id"] != request.execution_id:
            raise ExecutionJournalError("prepared_request_in_flight")

    txn_id = transaction_id or new_id()
    store.insert_habitat_execution_journal_prepared(
        execution_id=request.execution_id,
        request_id=request.request_id,
        canonical_payload_hash=payload_hash,
        payload_json=canon_json(
            {
                "request_id": request.request_id,
                "execution_id": request.execution_id,
                "target_object_id": request.target_object_id,
                "affordance_id": request.affordance_id,
            }
        ),
        transaction_id=txn_id,
        prepared_tick=int(prepared_tick),
    )
    row = store.get_habitat_execution_journal(request.execution_id)
    assert row is not None
    return _prepared_from_row(row)


def recover_execution(
    store: Store,
    execution_id: str,
    *,
    agent_id: str,
) -> ManipulationCommitResult | None:
    row = store.get_habitat_execution_journal(execution_id)
    if row is None:
        return None
    if row["status"] in (STATUS_COMMITTED_SUCCESS, STATUS_COMMITTED_FAILURE):
        return _terminal_result_from_row(store, row, agent_id=agent_id)
    if row["status"] != STATUS_PREPARED:
        return None

    recovered = store.find_habitat_execution_commit_evidence(
        execution_id=execution_id,
        transaction_id=row["transaction_id"],
        agent_id=agent_id,
    )
    if recovered is None:
        return ManipulationCommitResult(
            execution_id=execution_id,
            request_id=row["request_id"],
            journal_status=STATUS_PREPARED,
            outcome=None,
            failure_code=None,
            idempotent_replay=False,
        )

    store.finalize_habitat_execution_journal_recovery(
        execution_id=execution_id,
        status=recovered["status"],
        outcome_id=recovered.get("outcome_id"),
        failure_code=recovered.get("failure_code"),
    )
    row = store.get_habitat_execution_journal(execution_id)
    assert row is not None
    return _terminal_result_from_row(store, row, agent_id=agent_id)


def commit_manipulation_transaction(
    store: Store,
    governance: Governance,
    habitat_engine: HabitatEngine,
    physiology: Physiology,
    request: ManipulationRequest,
    validation: AffordanceValidationResult,
    *,
    agent_id: str,
    prepared_tick: int,
    monotonic_time: float,
    wall_time: float,
    transaction_id: str | None = None,
    crash_after_stage: int | None = None,
) -> ManipulationCommitResult:
    payload_hash = canonical_payload_hash(request)
    existing = store.get_habitat_execution_journal(request.execution_id)
    if existing is not None:
        if existing["canonical_payload_hash"] != payload_hash:
            raise ExecutionJournalError(EXECUTION_PAYLOAD_MISMATCH)
        if existing["status"] in (STATUS_COMMITTED_SUCCESS, STATUS_COMMITTED_FAILURE):
            if existing["status"] == STATUS_COMMITTED_SUCCESS:
                _maybe_rehydrate_committed_success(
                    store,
                    governance,
                    habitat_engine,
                    physiology,
                    existing,
                    agent_id=agent_id,
                    request=request,
                    validation=validation,
                )
            return _terminal_result_from_row(
                store,
                existing,
                agent_id=agent_id,
                idempotent_replay=True,
            )

    prepared = prepare_execution(
        store,
        request,
        prepared_tick=prepared_tick,
        transaction_id=transaction_id,
    )

    existing = store.get_habitat_execution_journal(request.execution_id)
    assert existing is not None
    if existing["status"] in (STATUS_COMMITTED_SUCCESS, STATUS_COMMITTED_FAILURE):
        if existing["status"] == STATUS_COMMITTED_SUCCESS:
            _maybe_rehydrate_committed_success(
                store,
                governance,
                habitat_engine,
                physiology,
                existing,
                agent_id=agent_id,
                request=request,
                validation=validation,
            )
        return _terminal_result_from_row(
            store,
            existing,
            agent_id=agent_id,
            idempotent_replay=True,
        )

    if existing["canonical_payload_hash"] != payload_hash:
        raise ExecutionJournalError(EXECUTION_PAYLOAD_MISMATCH)

    recovery = recover_execution(store, request.execution_id, agent_id=agent_id)
    if recovery is not None and recovery.journal_status in (
        STATUS_COMMITTED_SUCCESS,
        STATUS_COMMITTED_FAILURE,
    ):
        if recovery.journal_status == STATUS_COMMITTED_SUCCESS:
            row = store.get_habitat_execution_journal(request.execution_id)
            assert row is not None
            _maybe_rehydrate_committed_success(
                store,
                governance,
                habitat_engine,
                physiology,
                row,
                agent_id=agent_id,
                request=request,
                validation=validation,
            )
        return replace(recovery, idempotent_replay=True)

    if not validation.allowed:
        return _commit_failure(
            store,
            governance,
            habitat_engine,
            physiology,
            request,
            validation,
            prepared=prepared,
            agent_id=agent_id,
            monotonic_time=monotonic_time,
            wall_time=wall_time,
            failure_code=validation.failure_code or "AFFORDANCE_PRECONDITION_FAILED",
            crash_after_stage=crash_after_stage,
        )

    assert validation.effect_plan is not None
    return _commit_success(
        store,
        governance,
        habitat_engine,
        physiology,
        request,
        validation.effect_plan,
        prepared=prepared,
        agent_id=agent_id,
        monotonic_time=monotonic_time,
        wall_time=wall_time,
        crash_after_stage=crash_after_stage,
    )


def _prepared_from_row(row: dict[str, Any]) -> PreparedExecution:
    return PreparedExecution(
        execution_id=str(row["execution_id"]),
        request_id=str(row["request_id"]),
        status=str(row["status"]),
        canonical_payload_hash=str(row["canonical_payload_hash"]),
        transaction_id=str(row["transaction_id"]),
        prepared_tick=int(row["prepared_tick"]),
        outcome_id=str(row["outcome_id"]) if row.get("outcome_id") else None,
        failure_code=str(row["failure_code"]) if row.get("failure_code") else None,
    )


def _maybe_rehydrate_committed_success(
    store: Store,
    governance: Governance,
    habitat_engine: HabitatEngine,
    physiology: Physiology,
    row: dict[str, Any],
    *,
    agent_id: str,
    request: ManipulationRequest | None = None,
    validation: AffordanceValidationResult | None = None,
) -> None:
    """Idempotent catch-up when durable commit succeeded but in-memory state lags."""
    outcome_id = row.get("outcome_id")
    if not outcome_id:
        return
    outcome = store.get_verified_outcome_by_id(str(outcome_id), agent_id=agent_id)
    if outcome is None or not outcome.success:
        return

    txn_events = store.list_habitat_events_for_execution(
        agent_id=agent_id,
        execution_id=str(row["execution_id"]),
        transaction_id=str(row["transaction_id"]),
    )
    if not txn_events:
        return

    expected_hash = str(txn_events[-1]["payload"]["new_state_hash"])
    if habitat_engine.snapshot_view().state_hash == expected_hash:
        return

    if validation is not None and validation.effect_plan is not None and request is not None:
        state_after, _ = _apply_effect_plan(
            habitat_engine.state,
            validation.effect_plan,
            envelope_kwargs={
                "transaction_id": str(row["transaction_id"]),
                "request_id": str(row["request_id"]),
                "execution_id": str(row["execution_id"]),
                "actor_ref": request.body_instance_id,
                "target_ref": request.target_object_id,
            },
        )
        if state_after.state_hash == expected_hash:
            habitat_engine._state = state_after
            habitat_engine._rebuild_indexes()
            governance.apply_physiology(physiology, outcome)
            return

    state = habitat_engine.state
    for event in txn_events:
        state = _rehydrate_apply_event(state, event)
    habitat_engine._state = state  # ponytail: replay durable txn events post-COMMIT
    habitat_engine._rebuild_indexes()
    governance.apply_physiology(physiology, outcome)


def _rehydrate_apply_event(state: HabitatState, event: dict[str, Any]) -> HabitatState:
    payload = event["payload"]
    if (
        state.state_version == int(payload["new_state_version"])
        and state.state_hash == payload["new_state_hash"]
    ):
        return state
    try:
        return apply_habitat_event(state, event)
    except HabitatEventError as exc:
        if str(exc) != "event_new_state_version_mismatch":
            raise
        return _apply_terminal_snapshot_from_event(state, event)


def _apply_terminal_snapshot_from_event(state: HabitatState, event: dict[str, Any]) -> HabitatState:
    """Apply durable terminal snapshot when one event spans multiple commit mutations."""
    payload = event["payload"]
    event_type = event["event_type"]
    object_id = str(payload["object_id"]) if "object_id" in payload else None

    def snap(mutated: HabitatState) -> HabitatState:
        bumped = replace(
            mutated,
            state_version=int(payload["new_state_version"]),
            state_hash="",
        )
        result = with_state_hash(bumped)
        if result.state_hash != payload["new_state_hash"]:
            raise ExecutionJournalError("rehydrate_hash_mismatch")
        return result

    if event_type == HABITAT_OBJECT_STATE_CHANGED:
        assert object_id is not None
        new_obj_state = _object_state_from_payload(payload["new_state"])

        def change_state(obj: HabitatObject) -> HabitatObject:
            return replace(obj, state=new_obj_state)

        updated = apply_committed_object_mutation(state.objects[object_id], change_state)
        objects = dict(state.objects)
        objects[object_id] = updated
        return snap(replace(state, objects=objects))

    if event_type == HABITAT_OBJECT_MOVED:
        assert object_id is not None
        location = _location_from_payload(payload["new_location"])

        def move(obj: HabitatObject) -> HabitatObject:
            return replace(obj, location=location)

        updated = apply_committed_object_mutation(state.objects[object_id], move)
        objects = dict(state.objects)
        objects[object_id] = updated
        return snap(replace(state, objects=objects))

    if event_type == HABITAT_OBJECT_PICKED_UP:
        assert object_id is not None
        location = _location_from_payload(payload["new_location"])

        def pick_up(obj: HabitatObject) -> HabitatObject:
            return replace(obj, location=location)

        updated = apply_committed_object_mutation(state.objects[object_id], pick_up)
        objects = dict(state.objects)
        objects[object_id] = updated
        return snap(replace(state, objects=objects))

    if event_type == HABITAT_OBJECT_PLACED:
        assert object_id is not None
        location = _location_from_payload(payload["new_location"])

        def place(obj: HabitatObject) -> HabitatObject:
            return replace(obj, location=location)

        updated = apply_committed_object_mutation(state.objects[object_id], place)
        objects = dict(state.objects)
        objects[object_id] = updated
        return snap(replace(state, objects=objects))

    if event_type in (HABITAT_AFFORDANCE_ACTIVATED, HABITAT_AFFORDANCE_DEACTIVATED):
        assert object_id is not None
        new_obj_state = _object_state_from_payload(payload["new_state"])

        def change_state(obj: HabitatObject) -> HabitatObject:
            return replace(obj, state=new_obj_state)

        updated = apply_committed_object_mutation(state.objects[object_id], change_state)
        objects = dict(state.objects)
        objects[object_id] = updated
        return snap(replace(state, objects=objects))

    raise ExecutionJournalError(f"rehydrate_unsupported_event:{event_type}")


def _terminal_result_from_row(
    store: Store,
    row: dict[str, Any],
    *,
    agent_id: str,
    idempotent_replay: bool = False,
) -> ManipulationCommitResult:
    outcome = None
    if row.get("outcome_id"):
        outcome = store.get_verified_outcome_by_id(str(row["outcome_id"]), agent_id=agent_id)
    return ManipulationCommitResult(
        execution_id=str(row["execution_id"]),
        request_id=str(row["request_id"]),
        journal_status=str(row["status"]),
        outcome=outcome,
        failure_code=str(row["failure_code"]) if row.get("failure_code") else None,
        idempotent_replay=idempotent_replay,
    )


def _commit_failure(
    store: Store,
    governance: Governance,
    habitat_engine: HabitatEngine,
    physiology: Physiology,
    request: ManipulationRequest,
    validation: AffordanceValidationResult,
    *,
    prepared: PreparedExecution,
    agent_id: str,
    monotonic_time: float,
    wall_time: float,
    failure_code: str,
    crash_after_stage: int | None,
) -> ManipulationCommitResult:
    habitat_hash_before = habitat_engine.snapshot_view().state_hash
    phys_before = physiology.as_dict()
    outcome = governance.verify_manipulation_outcome(
        request,
        success=False,
        failure_code=failure_code,
        physiology_effects={},
        applied_parameters=validation.applied_parameters,
        transaction_id=prepared.transaction_id,
    )

    def stage_journal() -> None:
        store.update_habitat_execution_journal_terminal(
            execution_id=prepared.execution_id,
            status=STATUS_COMMITTED_FAILURE,
            outcome_id=outcome.outcome_id,
            failure_code=failure_code,
        )

    def stage_outcome() -> None:
        store.append_event(
            agent_id=agent_id,
            event_type="outcome_verified",
            monotonic_time=monotonic_time,
            wall_time=wall_time,
            payload={
                "outcome_id": outcome.outcome_id,
                "execution_id": request.execution_id,
                "request_id": request.request_id,
                "capability": request.capability,
                "success": False,
                "reason": failure_code,
                "effects": {},
                "verified": True,
                "raw": outcome.raw,
            },
            event_id=outcome.outcome_id,
        )

    def on_commit() -> None:
        assert habitat_engine.snapshot_view().state_hash == habitat_hash_before
        assert physiology.as_dict() == phys_before

    store.atomic_manipulation_outcome(
        [stage_journal, stage_outcome],
        on_commit=on_commit,
        crash_after_stage=crash_after_stage,
    )
    return ManipulationCommitResult(
        execution_id=request.execution_id,
        request_id=request.request_id,
        journal_status=STATUS_COMMITTED_FAILURE,
        outcome=outcome,
        failure_code=failure_code,
    )


def _commit_success(
    store: Store,
    governance: Governance,
    habitat_engine: HabitatEngine,
    physiology: Physiology,
    request: ManipulationRequest,
    effect_plan: HabitatEffectPlan,
    *,
    prepared: PreparedExecution,
    agent_id: str,
    monotonic_time: float,
    wall_time: float,
    crash_after_stage: int | None,
) -> ManipulationCommitResult:
    state_before = habitat_engine.state
    try:
        state_after, habitat_events = _apply_effect_plan(
            state_before,
            effect_plan,
            envelope_kwargs={
                "transaction_id": prepared.transaction_id,
                "request_id": request.request_id,
                "execution_id": request.execution_id,
                "actor_ref": request.body_instance_id,
                "target_ref": request.target_object_id,
            },
        )
    except MutationRejected as exc:
        code = str(exc)
        if code not in {
            HABITAT_COLLECTION_CAP_EXCEEDED,
            EVENT_STORAGE_BUDGET_EXCEEDED,
        }:
            code = str(exc)
        validation_stub = AffordanceValidationResult(
            allowed=False,
            failure_code=code,
            expected_object_version=None,
            expected_habitat_version=None,
            effect_plan=None,
            applied_parameters=None,
        )
        return _commit_failure(
            store,
            governance,
            habitat_engine,
            physiology,
            request,
            validation_stub,
            prepared=prepared,
            agent_id=agent_id,
            monotonic_time=monotonic_time,
            wall_time=wall_time,
            failure_code=code,
            crash_after_stage=crash_after_stage,
        )

    phys_effects = organism_effects_to_physiology(effect_plan.requested_organism_effects)
    outcome = governance.verify_manipulation_outcome(
        request,
        success=True,
        failure_code=None,
        physiology_effects=phys_effects,
        applied_parameters=None,
        transaction_id=prepared.transaction_id,
    )

    habitat_event_records: list[dict[str, Any]] = []

    def stage_habitat_events() -> None:
        nonlocal habitat_event_records
        for event in habitat_events:
            store.append_event(
                agent_id=agent_id,
                event_type=event["event_type"],
                monotonic_time=monotonic_time,
                wall_time=wall_time,
                payload=event["payload"],
                event_id=event["event_id"],
            )
            habitat_event_records.append(event)

    def stage_organism_effects() -> None:
        if not effect_plan.requested_organism_effects:
            return
        store.append_event(
            agent_id=agent_id,
            event_type="organism_effect_applied",
            monotonic_time=monotonic_time,
            wall_time=wall_time,
            payload={
                "execution_id": request.execution_id,
                "request_id": request.request_id,
                "effects": list(effect_plan.requested_organism_effects),
            },
        )

    def stage_outcome() -> None:
        store.append_event(
            agent_id=agent_id,
            event_type="outcome_verified",
            monotonic_time=monotonic_time,
            wall_time=wall_time,
            payload={
                "outcome_id": outcome.outcome_id,
                "execution_id": request.execution_id,
                "request_id": request.request_id,
                "capability": request.capability,
                "success": True,
                "reason": "manipulation_committed",
                "effects": phys_effects,
                "verified": True,
                "raw": outcome.raw,
            },
            event_id=outcome.outcome_id,
        )

    def stage_journal() -> None:
        store.update_habitat_execution_journal_terminal(
            execution_id=prepared.execution_id,
            status=STATUS_COMMITTED_SUCCESS,
            outcome_id=outcome.outcome_id,
            failure_code=None,
        )

    def on_commit() -> None:
        habitat_engine._state = state_after  # ponytail: journal owns txn; engine catches up post-COMMIT
        habitat_engine._rebuild_indexes()
        governance.apply_physiology(physiology, outcome)

    try:
        store.atomic_manipulation_outcome(
            [stage_habitat_events, stage_organism_effects, stage_outcome, stage_journal],
            on_commit=on_commit,
            crash_after_stage=crash_after_stage,
        )
    except MutationRejected as exc:
        if str(exc) != EVENT_STORAGE_BUDGET_EXCEEDED:
            raise
        validation_stub = AffordanceValidationResult(
            allowed=False,
            failure_code=EVENT_STORAGE_BUDGET_EXCEEDED,
            expected_object_version=None,
            expected_habitat_version=None,
            effect_plan=None,
            applied_parameters=None,
        )
        return _commit_failure(
            store,
            governance,
            habitat_engine,
            physiology,
            request,
            validation_stub,
            prepared=prepared,
            agent_id=agent_id,
            monotonic_time=monotonic_time,
            wall_time=wall_time,
            failure_code=EVENT_STORAGE_BUDGET_EXCEEDED,
            crash_after_stage=crash_after_stage,
        )
    return ManipulationCommitResult(
        execution_id=request.execution_id,
        request_id=request.request_id,
        journal_status=STATUS_COMMITTED_SUCCESS,
        outcome=outcome,
        failure_code=None,
    )


def _apply_effect_plan(
    state: HabitatState,
    effect_plan: HabitatEffectPlan,
    *,
    envelope_kwargs: dict[str, Any],
) -> tuple[HabitatState, list[dict[str, Any]]]:
    state_before = state
    state_after = _apply_all_mutations(state_before, effect_plan.habitat_mutations)
    events = [
        _build_event_for_stub(state_before, state_after, stub, envelope_kwargs=envelope_kwargs)
        for stub in effect_plan.habitat_events
    ]
    return state_after, events


def _apply_all_mutations(state: HabitatState, mutations: tuple[dict[str, Any], ...]) -> HabitatState:
    current = state
    for mutation in mutations:
        current = _apply_one_mutation(current, mutation)
    return current


def _apply_one_mutation(state: HabitatState, mutation: dict[str, Any]) -> HabitatState:
    object_id = str(mutation["object_id"])
    kind = str(mutation["mutation_kind"])

    def mutate(obj: HabitatObject) -> HabitatObject:
        if kind == "SET_LOCATION":
            loc = mutation["location"]
            if loc["mode"] == "HELD_BY":
                new_loc = HeldByLocation(
                    body_instance_id=str(loc["body_instance_id"]),
                    attachment_generation=int(loc["attachment_generation"]),
                    hold_slot=int(loc["hold_slot"]),
                )
            else:
                zone_id = str(loc.get("zone_id") or "")
                if zone_id:
                    count = sum(
                        1
                        for oid, o in state.objects.items()
                        if oid != object_id
                        and isinstance(o.location, FreeLocation)
                        and o.location.zone_id == zone_id
                    )
                    zone = state.zones.get(zone_id)
                    if zone is not None and count >= zone.occupancy_limit:
                        raise MutationRejected(HABITAT_COLLECTION_CAP_EXCEEDED)
                new_loc = FreeLocation(float(loc["x"]), float(loc["y"]), zone_id)
            return replace(obj, location=new_loc)
        if kind == "SET_ACTIVATABLE_ACTIVE":
            return replace(obj, state=ActivatableState(active=bool(mutation["active"])))
        if kind == "APPLY_WORLD_EFFECT":
            field = str(mutation["field"])
            delta = mutation["delta"]
            from umbra_core.habitat_affordances.definitions import WorldEffectMutation

            new_state = _apply_world_effect_mutations(
                obj.state,
                (WorldEffectMutation(field=field, delta=delta),),
            )
            return replace(obj, state=new_state)
        if kind == "SET_COOLDOWN":
            aff_id = str(mutation["affordance_id"])
            until = int(mutation["cooldown_until_tick"])
            cooldowns = [(a, t) for a, t in obj.cooldowns if a != aff_id]
            cooldowns.append((aff_id, until))
            return replace(obj, cooldowns=tuple(sorted(cooldowns)))
        raise MutationRejected(f"unknown_mutation_kind:{kind}")

    obj = state.objects.get(object_id)
    if obj is None:
        raise MutationRejected(f"missing_object:{object_id}")
    updated = apply_committed_object_mutation(obj, mutate)
    objects = dict(state.objects)
    objects[object_id] = updated
    bumped = replace(state, objects=objects, state_version=state.state_version + 1)
    return with_state_hash(bumped)


def _build_event_for_stub(
    state_before: HabitatState,
    state_after: HabitatState,
    stub: dict[str, Any],
    *,
    envelope_kwargs: dict[str, Any],
) -> dict[str, Any]:
    event_type = str(stub["event_type"])
    object_id = str(stub["object_id"])
    if event_type == HABITAT_OBJECT_PICKED_UP:
        return build_object_picked_up_event(state_before, state_after, object_id, **envelope_kwargs)
    if event_type == HABITAT_OBJECT_PLACED:
        return build_object_placed_event(state_before, state_after, object_id, **envelope_kwargs)
    if event_type == HABITAT_OBJECT_MOVED:
        return build_object_moved_event(state_before, state_after, object_id, **envelope_kwargs)
    if event_type == HABITAT_OBJECT_STATE_CHANGED:
        return build_habitat_event(
            state_before,
            state_after,
            HABITAT_OBJECT_STATE_CHANGED,
            extra_payload={"object_id": object_id, "new_state": stub["new_state"]},
            **envelope_kwargs,
        )
    if event_type in (HABITAT_AFFORDANCE_ACTIVATED, HABITAT_AFFORDANCE_DEACTIVATED):
        new_state = state_after.objects[object_id].state
        from umbra_core.habitat.events import object_state_to_payload

        return build_habitat_event(
            state_before,
            state_after,
            event_type,
            extra_payload={"object_id": object_id, "new_state": object_state_to_payload(new_state)},
            **envelope_kwargs,
        )
    raise MutationRejected(f"unsupported_habitat_event_stub:{event_type}")
