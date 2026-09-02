"""Immutable same-tick planning evidence frames for AS-003P shadow use.

The builder consumes explicit policy-authorized snapshots only. It has no
Habitat import and cannot read world coordinates or execute an action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Iterable, Mapping, Sequence

from umbra_core.decision_trace import canonical_fingerprint
from umbra_core.self_model.engine import SupportSemantics
from umbra_core.world_model.engine import FactKind, PERSISTENCE_DECAY_PER_TICK
from umbra_core.world_model.route_evidence import (
    ROUTE_EVIDENCE_SCHEMA,
    ROUTE_EVIDENCE_SCHEMA_V1,
    TERMINAL_BY_KIND,
)

from .core import FrozenMap


PLANNING_FRAME_SCHEMA_V1 = "AS003P_PLANNING_EVIDENCE_FRAME_V1"
PLANNING_FRAME_SCHEMA = "AS003P_PLANNING_EVIDENCE_FRAME_V2"
MAX_PLANNING_DEPTH = 5
WORLD_ENTITY_RETENTION_FLOOR = 0.05
OPPORTUNITY_KINDS = frozenset({"resource", "novel_crystal", "rest", "inspect"})


class PlanningModality(str, Enum):
    MUST = "MUST"
    MAY = "MAY"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class ModalFact:
    modality: PlanningModality
    temporal_scope: str
    value: Any = None
    valid_through_ticks: int | None = None
    provenance: tuple[str, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "modality", PlanningModality(self.modality))
        object.__setattr__(self, "value", _freeze(self.value))
        object.__setattr__(self, "provenance", tuple(sorted({str(x)[:160] for x in self.provenance})))
        object.__setattr__(self, "reason", str(self.reason)[:160])
        if self.valid_through_ticks is not None and int(self.valid_through_ticks) < 0:
            raise ValueError("negative modal horizon")

    def to_canonical(self) -> dict[str, Any]:
        return {
            "modality": self.modality.value,
            "temporal_scope": self.temporal_scope,
            "value": _plain(self.value),
            "valid_through_ticks": self.valid_through_ticks,
            "provenance": list(self.provenance),
            "reason": self.reason,
        }


def _freeze(value: Any) -> Any:
    if isinstance(value, FrozenMap):
        return value
    if isinstance(value, Mapping):
        return FrozenMap(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite frame value")
        return value
    raise TypeError(f"unsupported mutable frame value: {type(value)!r}")


def _plain(value: Any) -> Any:
    if isinstance(value, FrozenMap):
        return value.to_plain()
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, ModalFact):
        return value.to_canonical()
    return value


def modality_from_support_semantics(semantics: str) -> PlanningModality:
    semantics = str(semantics)
    if semantics in {
        SupportSemantics.HARD_CONTRACT.value,
        SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value,
    }:
        return PlanningModality.MUST
    if semantics == SupportSemantics.PROBABILISTIC_SUPPORT.value:
        return PlanningModality.MAY
    if semantics == SupportSemantics.NOT_APPLICABLE.value:
        return PlanningModality.UNSUPPORTED
    return PlanningModality.UNKNOWN


def _support_fact(row: Mapping[str, Any], *, provenance: str) -> ModalFact:
    minimum, maximum = row.get("minimum"), row.get("maximum")
    modality = modality_from_support_semantics(str(row.get("semantics", SupportSemantics.UNKNOWN.value)))
    if minimum is None or maximum is None:
        modality = PlanningModality.UNKNOWN if modality is not PlanningModality.UNSUPPORTED else modality
    return ModalFact(
        modality,
        "capability-performance",
        {"minimum": minimum, "maximum": maximum},
        provenance=tuple((*tuple(row.get("provenance") or ()), provenance)),
        reason="source-support-semantics",
    )


def _retention_horizon(entity: Mapping[str, Any], *, object_persistence: bool) -> int | None:
    if not object_persistence:
        return None
    confidence = float(entity.get("confidence", 0.0))
    if confidence < WORLD_ENTITY_RETENTION_FLOOR:
        return None
    landmark = bool(
        entity.get("distance_support_upper_bound") is not None
        and (
            str(entity.get("entity_kind")) in {"resource", "novel_crystal"}
            or (
                str(entity.get("entity_kind")) == "rest"
                and int(entity.get("verified_recovery_count", 0)) > 0
            )
        )
    )
    if landmark:
        return MAX_PLANNING_DEPTH
    decay = PERSISTENCE_DECAY_PER_TICK * (
        0.35 if int(entity.get("verified_recovery_count", 0)) > 0 else 1.0
    )
    if decay <= 0.0:
        return MAX_PLANNING_DEPTH
    return min(MAX_PLANNING_DEPTH, max(0, int(math.floor((confidence - WORLD_ENTITY_RETENTION_FLOOR) / decay + 1e-12))))


def opportunity_fact_from_world_entity(
    entity: Mapping[str, Any],
    *,
    root_tick: int,
    body_schema_identity: str,
    object_persistence: bool,
) -> ModalFact:
    """Return only the future component for compatibility with pure callers."""
    return ModalFact(**_opportunity_modal_evidence(
        entity,
        root_tick=root_tick,
        body_schema_identity=body_schema_identity,
        object_persistence=object_persistence,
    )["future_fact"])


def _opportunity_modal_evidence(
    entity: Mapping[str, Any],
    *,
    root_tick: int,
    body_schema_identity: str,
    object_persistence: bool,
) -> dict[str, Any]:
    """Keep root-current and future-belief propositions explicitly additive."""
    if int(entity.get("last_tick", root_tick)) > int(root_tick):
        raise ValueError("future world entity joined into frame")
    identity = str(entity.get("entity_id", ""))
    kind = str(entity.get("entity_kind", ""))
    if not identity or kind not in OPPORTUNITY_KINDS:
        unsupported = ModalFact(PlanningModality.UNSUPPORTED, "root-current", reason="not-planning-opportunity")
        return {
            "identity": identity,
            "kind": kind,
            "current": unsupported.to_canonical(),
            "future": unsupported.to_canonical(),
            "future_fact": {
                "modality": unsupported.modality,
                "temporal_scope": unsupported.temporal_scope,
                "value": unsupported.value,
                "valid_through_ticks": unsupported.valid_through_ticks,
                "provenance": unsupported.provenance,
                "reason": unsupported.reason,
            },
        }
    if str(entity.get("support_body_schema_id") or "") != str(body_schema_identity):
        current = ModalFact(PlanningModality.UNKNOWN, "root-current", provenance=(f"world:{identity}",), reason="body-schema-mismatch")
        future = ModalFact(PlanningModality.UNKNOWN, "future-belief-support", provenance=(f"world:{identity}",), reason="body-schema-mismatch")
        return _opportunity_row(identity, kind, current, future)
    support = entity.get("distance_support_upper_bound")
    if support is None or not math.isfinite(float(support)) or float(support) < 0.0:
        current = ModalFact(PlanningModality.UNKNOWN, "root-current", provenance=(f"world:{identity}",), reason="bounded-support-missing")
        future = ModalFact(PlanningModality.UNKNOWN, "future-belief-support", provenance=(f"world:{identity}",), reason="bounded-support-missing")
        return _opportunity_row(identity, kind, current, future)
    fact_kind = str(entity.get("fact_kind", FactKind.UNKNOWN.value))
    last_tick = int(entity.get("last_tick", root_tick))
    current_modality = PlanningModality.MUST if (
        fact_kind == FactKind.CURRENT_OBSERVATION.value and last_tick == int(root_tick)
    ) else (
        PlanningModality.MAY if fact_kind == FactKind.REMEMBERED_ESTIMATE.value else PlanningModality.UNKNOWN
    )
    current = ModalFact(
        current_modality,
        "root-current",
        {
            "identity": identity,
            "kind": kind,
            "distance_support_upper_bound": float(support),
            "fact_kind": fact_kind,
            "source_tick": last_tick,
        },
        valid_through_ticks=0,
        provenance=(str(entity.get("support_provenance") or f"world:{identity}"),),
        reason="same-tick-current-observation" if current_modality is PlanningModality.MUST else (
            "remembered-current-possibility" if current_modality is PlanningModality.MAY else "not-current-at-root"
        ),
    )
    horizon = _retention_horizon(entity, object_persistence=object_persistence)
    future_modality = PlanningModality.MAY if horizon is not None and horizon > 0 else PlanningModality.UNKNOWN
    future = ModalFact(
        future_modality,
        "future-belief-support",
        {
            "identity": identity,
            "kind": kind,
            "distance_support_upper_bound": float(support),
            "fact_kind": fact_kind,
            "source_tick": last_tick,
        },
        valid_through_ticks=horizon,
        provenance=(str(entity.get("support_provenance") or f"world:{identity}"),),
        reason="existing-world-model-retention" if future_modality is PlanningModality.MAY else "future-persistence-not-supported",
    )
    return _opportunity_row(identity, kind, current, future)


def _opportunity_row(identity: str, kind: str, current: ModalFact, future: ModalFact) -> dict[str, Any]:
    return {
        "identity": identity,
        "kind": kind,
        "current": current.to_canonical(),
        "future": future.to_canonical(),
        "future_fact": {
            "modality": future.modality,
            "temporal_scope": future.temporal_scope,
            "value": future.value,
            "valid_through_ticks": future.valid_through_ticks,
            "provenance": future.provenance,
            "reason": future.reason,
        },
    }


@dataclass(frozen=True)
class PlanningEvidenceFrame:
    organism_tick: int
    organism_age: int
    monotonic_time: float
    physiology_root: FrozenMap
    body: FrozenMap
    constitutional_capabilities: FrozenMap
    capability_support: FrozenMap
    opportunities: FrozenMap
    route_support: FrozenMap
    service_timing: FrozenMap
    pending_execution: FrozenMap
    source_versions: FrozenMap
    route_experience_support: FrozenMap = field(default_factory=FrozenMap)
    affordance_support: FrozenMap = field(default_factory=FrozenMap)
    candidate_frame_identity: str | None = None
    material_fingerprint: str = ""
    schema: str = PLANNING_FRAME_SCHEMA

    def __post_init__(self) -> None:
        if int(self.organism_tick) < 0 or int(self.organism_age) < 0:
            raise ValueError("negative planning tick")
        for name in (
            "physiology_root", "body", "constitutional_capabilities",
            "capability_support", "opportunities", "route_support",
            "service_timing", "pending_execution", "source_versions",
            "route_experience_support", "affordance_support",
        ):
            value = getattr(self, name)
            object.__setattr__(self, name, value if isinstance(value, FrozenMap) else FrozenMap(value))
        expected = canonical_fingerprint(self._canonical_without_fingerprint())
        if self.material_fingerprint and self.material_fingerprint != expected:
            raise ValueError("planning frame fingerprint mismatch")
        object.__setattr__(self, "material_fingerprint", expected)

    def _canonical_without_fingerprint(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "organism_tick": self.organism_tick,
            "organism_age": self.organism_age,
            "monotonic_time": self.monotonic_time,
            "physiology_root": _plain(self.physiology_root),
            "body": _plain(self.body),
            "constitutional_capabilities": _plain(self.constitutional_capabilities),
            "capability_support": _plain(self.capability_support),
            "opportunities": _plain(self.opportunities),
            "route_support": _plain(self.route_support),
            "service_timing": _plain(self.service_timing),
            "pending_execution": _plain(self.pending_execution),
            "source_versions": _plain(self.source_versions),
            "route_experience_support": _plain(self.route_experience_support),
            "affordance_support": _plain(self.affordance_support),
            "candidate_frame_identity": self.candidate_frame_identity,
        }

    def to_canonical(self) -> dict[str, Any]:
        return {**self._canonical_without_fingerprint(), "material_fingerprint": self.material_fingerprint}

    def bind_candidates(self, views: Sequence[Mapping[str, Any]]) -> "PlanningEvidenceFrame":
        identities = sorted({str(view.get("identity", "")) for view in views if view.get("identity")})
        candidate_identity = canonical_fingerprint(identities)
        return PlanningEvidenceFrame(
            organism_tick=self.organism_tick,
            organism_age=self.organism_age,
            monotonic_time=self.monotonic_time,
            physiology_root=self.physiology_root,
            body=self.body,
            constitutional_capabilities=self.constitutional_capabilities,
            capability_support=self.capability_support,
            opportunities=self.opportunities,
            route_support=self.route_support,
            service_timing=self.service_timing,
            pending_execution=self.pending_execution,
            source_versions=self.source_versions,
            route_experience_support=self.route_experience_support,
            affordance_support=self.affordance_support,
            candidate_frame_identity=candidate_identity,
            schema=self.schema,
        )


def _route_step_projection(step: Mapping[str, Any]) -> dict[str, Any]:
    """Copy only the immutable, observed route-control witness fields."""
    return {
        "capability": str(step.get("capability", "")),
        "issue_tick": int(step.get("issue_tick", 0)),
        "completion_tick": int(step.get("completion_tick", 0)),
        "completion_lag": int(step.get("completion_lag", 0)),
        "translational_movement": bool(step.get("translational_movement", False)),
        "success": bool(step.get("success", False)),
        "verified_outcome_ref": step.get("verified_outcome_ref"),
    }


def _route_witness_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    steps = tuple(_route_step_projection(step) for step in record.get("route_control_steps", ()))
    if not steps:
        raise ValueError("v2_route_witness_requires_control_steps")
    first_issue = steps[0]["issue_tick"]
    final_completion = steps[-1]["completion_tick"]
    return {
        "route_evidence_id": str(record.get("evidence_id", "")),
        "opportunity_entity_id": str(record.get("opportunity_entity_id", "")),
        "body_schema_id": str(record.get("body_schema_id", "")),
        "terminal_capability": str(record.get("terminal_capability", "")),
        "first_route_control_issue_tick": first_issue,
        "final_terminal_completion_tick": final_completion,
        "observed_episode_ticks": final_completion - first_issue + 1,
        "ordered_control_steps": steps,
        "verified_movement_execution_count": int(record.get("verified_movement_execution_count", 0)),
        "route_control_execution_count": len(steps),
        "observed_route_control_completion_lags": tuple(
            int(step["completion_lag"]) for step in steps
        ),
        "terminal_completion_lag": record.get("terminal_completion_lag"),
        "source_outcome_references": tuple(str(ref) for ref in record.get("execution_outcome_refs", ())),
        "evidence_semantics": str(record.get("evidence_semantics", "")),
        "provenance": tuple(
            str(ref) for ref in record.get("execution_outcome_refs", ())
        ),
    }


def project_route_experience_support(
    route_evidence_state: Mapping[str, Any] | None,
    *,
    opportunities: Mapping[str, Any],
    body_schema_identity: str,
) -> dict[str, Any]:
    """Project route history into MAY/UNKNOWN evidence without interpolation."""
    records = tuple((route_evidence_state or {}).get("experiences", ()))
    result: dict[str, Any] = {}
    for identity, opportunity in sorted(opportunities.items()):
        kind = str(opportunity.get("kind", ""))
        terminal = TERMINAL_BY_KIND.get(kind)
        if terminal is None:
            continue
        current_row = opportunity.get("current", {})
        if str(current_row.get("reason", "")) == "body-schema-mismatch":
            result[str(identity)] = ModalFact(
                PlanningModality.UNKNOWN,
                "future-route-experience",
                {"opportunity_entity_id": str(identity), "body_schema_id": str(body_schema_identity), "terminal_capability": terminal, "witnesses": (), "failures": (), "v1_incomplete_count": 0},
                provenance=(f"world:{identity}",),
                reason="opportunity-body-schema-mismatch",
            ).to_canonical()
            continue
        matching = tuple(
            record for record in records
            if str(record.get("opportunity_entity_id", "")) == str(identity)
            and str(record.get("body_schema_id", "")) == str(body_schema_identity)
            and str(record.get("terminal_capability", "")) == terminal
        )
        witnesses: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        v1_incomplete = 0
        for record in matching:
            if str(record.get("schema", ROUTE_EVIDENCE_SCHEMA_V1)) == ROUTE_EVIDENCE_SCHEMA and bool(record.get("terminal_result")):
                try:
                    witnesses.append(_route_witness_projection(record))
                except (TypeError, ValueError):
                    v1_incomplete += 1
            elif not bool(record.get("terminal_result")):
                failure = {
                    "route_evidence_id": str(record.get("evidence_id", "")),
                    "opportunity_entity_id": str(record.get("opportunity_entity_id", "")),
                    "body_schema_id": str(record.get("body_schema_id", "")),
                    "terminal_capability": str(record.get("terminal_capability", "")),
                    "schema": str(record.get("schema", ROUTE_EVIDENCE_SCHEMA_V1)),
                    "route_failure_code": record.get("route_failure_code"),
                    "observed_failure_tick": record.get("final_tick"),
                    "execution_outcome_references": tuple(
                        str(ref) for ref in record.get("execution_outcome_refs", ())
                    ),
                    "evidence_semantics": str(record.get("evidence_semantics", "")),
                    "ordered_control_steps": tuple(
                        _route_step_projection(step)
                        for step in record.get("route_control_steps", ())
                    ),
                }
                failures.append(failure)
            else:
                v1_incomplete += 1
        witnesses.sort(key=lambda row: (row["first_route_control_issue_tick"], row["route_evidence_id"]))
        failures.sort(key=lambda row: (int(row["observed_failure_tick"] or -1), row["route_evidence_id"]))
        modality = PlanningModality.MAY if witnesses else PlanningModality.UNKNOWN
        result[str(identity)] = ModalFact(
            modality,
            "future-route-experience",
            {
                "opportunity_entity_id": str(identity),
                "body_schema_id": str(body_schema_identity),
                "terminal_capability": terminal,
                "witnesses": tuple(witnesses),
                "failures": tuple(failures),
                "v1_incomplete_count": v1_incomplete,
            },
            provenance=tuple(
                sorted({
                    str(ref)
                    for row in (*witnesses, *failures)
                    for ref in row.get("provenance", row.get("execution_outcome_references", ()))
                    if ref
                })
            ),
            reason=("verified-v2-route-experience" if witnesses else "no-complete-v2-route-witness"),
        ).to_canonical()
    return result


def project_affordance_support(
    affordances: Mapping[str, Any] | None,
    *,
    opportunities: Mapping[str, Any],
    world_model_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Expose learned affordance facts; authored priors remain UNKNOWN."""
    fixed_authored = bool((world_model_config or {}).get("fixed_authored", False))
    instances_by_kind: dict[str, tuple[str, ...]] = {}
    for identity, opportunity in opportunities.items():
        instances_by_kind.setdefault(str(opportunity.get("kind", "")), tuple())
        instances_by_kind[str(opportunity.get("kind", ""))] += (str(identity),)
    result: dict[str, Any] = {}
    for affordance_id, raw in sorted((affordances or {}).items()):
        row = dict(raw)
        kind = str(row.get("entity_kind", ""))
        action = str(row.get("action", ""))
        status = str(row.get("status", "UNKNOWN"))
        source = "authored" if fixed_authored else "learned"
        active_learned_inspect = (
            source == "learned"
            and action == "inspect"
            and status == "ACTIVE"
            and bool(instances_by_kind.get(kind, ()))
        )
        result[str(affordance_id)] = ModalFact(
            PlanningModality.MAY if active_learned_inspect else PlanningModality.UNKNOWN,
            "future-affordance",
            {
                "affordance_id": str(affordance_id),
                "entity_kind": kind,
                "action": action,
                "support_count": int(row.get("support_count", 0)),
                "contradiction_count": int(row.get("contradiction_count", 0)),
                "status": status,
                "source": source,
                "opportunity_entity_ids": instances_by_kind.get(kind, ()),
            },
            provenance=(f"world-model-affordance:{affordance_id}",),
            reason=("learned-active-inspect-affordance" if active_learned_inspect else "affordance-not-lawful-for-planning"),
        ).to_canonical()
    return result


def build_planning_evidence_frame(
    *,
    organism_tick: int,
    organism_age: int,
    monotonic_time: float,
    physiology: Mapping[str, float],
    body_state: Mapping[str, Any],
    body_profile: Mapping[str, Any],
    self_model_body_schema: Mapping[str, Any],
    capability_support: Mapping[str, Mapping[str, Any]],
    world_entities: Iterable[Mapping[str, Any]],
    world_object_persistence: bool,
    pending_execution: Mapping[str, Any],
    source_versions: Mapping[str, Any],
    route_evidence_state: Mapping[str, Any] | None = None,
    world_affordances: Mapping[str, Any] | None = None,
    world_model_config: Mapping[str, Any] | None = None,
) -> PlanningEvidenceFrame:
    required = {"energy", "fatigue", "integrity", "stimulation"}
    if set(physiology) != required:
        raise ValueError("frame requires exact four-owner physiology")
    schema_id = str(self_model_body_schema.get("body_schema_id") or "")
    if not schema_id:
        raise ValueError("body schema identity required")
    capabilities = {
        str(cap): ModalFact(PlanningModality.MUST, "root-current", True, provenance=(f"body-profile:{body_profile.get('profile_id', 'legacy')}",), reason="constitutional-capability").to_canonical()
        for cap in body_profile.get("supported_capabilities", ())
    }
    support_rows: dict[str, Any] = {}
    for capability, envelope in capability_support.items():
        if str(envelope.get("body_schema_id") or "") != schema_id:
            support_rows[str(capability)] = {"progress": ModalFact(PlanningModality.UNKNOWN, "capability-performance", reason="body-schema-mismatch").to_canonical()}
            continue
        support_rows[str(capability)] = {
            name: _support_fact(dict(envelope.get(name) or {}), provenance=f"self-model:{capability}:{name}").to_canonical()
            for name in ("progress", "applied_step", "completion")
        }
    opportunities: dict[str, Any] = {}
    for entity in world_entities:
        if str(entity.get("entity_kind")) not in OPPORTUNITY_KINDS:
            continue
        fact = _opportunity_modal_evidence(
            entity,
            root_tick=organism_age,
            body_schema_identity=schema_id,
            object_persistence=world_object_persistence,
        )
        fact.pop("future_fact", None)
        opportunities[str(entity.get("entity_id"))] = fact
    actuator_delay = float(body_state.get("actuator_delay", 0.0))
    motion_ticks = int(actuator_delay) if actuator_delay >= 1.0 else 0
    timings = {
        cap: ModalFact(PlanningModality.MUST, "root-current", {"completion_ticks": motion_ticks if cap in {"MOVE", "APPROACH", "RETREAT"} else 0}, provenance=("runtime-execution-contract",), reason="existing-execution-contract").to_canonical()
        for cap in ("MOVE", "APPROACH", "RETREAT", "CHARGE", "REST", "INSPECT")
    }
    route_modality = PlanningModality.UNKNOWN
    approach = support_rows.get("APPROACH", {}).get("progress", {})
    if approach:
        route_modality = PlanningModality(str(approach.get("modality", PlanningModality.UNKNOWN.value)))
    routes = {
        identity: ModalFact(route_modality, "future-route", {"opportunity_identity": identity}, provenance=("self-model:APPROACH",), reason="body-relative-route-support").to_canonical()
        for identity in opportunities
    }
    route_experience_support = project_route_experience_support(
        route_evidence_state,
        opportunities=opportunities,
        body_schema_identity=schema_id,
    )
    affordance_support = project_affordance_support(
        world_affordances,
        opportunities=opportunities,
        world_model_config=world_model_config,
    )
    return PlanningEvidenceFrame(
        organism_tick=int(organism_tick), organism_age=int(organism_age), monotonic_time=float(monotonic_time),
        physiology_root=FrozenMap({k: float(physiology[k]) for k in sorted(required)}),
        body=FrozenMap(dict(body_profile)),
        constitutional_capabilities=FrozenMap(capabilities),
        capability_support=FrozenMap(support_rows),
        opportunities=FrozenMap(opportunities),
        route_support=FrozenMap(routes),
        service_timing=FrozenMap(timings),
        pending_execution=FrozenMap(dict(pending_execution)),
        source_versions=FrozenMap(dict(source_versions)),
        route_experience_support=FrozenMap(route_experience_support),
        affordance_support=FrozenMap(affordance_support),
    )
