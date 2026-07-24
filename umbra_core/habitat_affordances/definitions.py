"""Static AffordanceDefinition load and canonical hashing."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from enum import Enum
from pathlib import Path
from typing import Any

from umbra_core.habitat.state import ObjectKind, canonical_serialize
from umbra_core.util import canon_json, sha256_hex

AFFORDANCE_SCHEMA_VERSION = "d009.affordance-definitions.v1"
PRECONDITIONS_SCHEMA_VERSION = "d009.affordance-preconditions.v1"
BODY_REQUIREMENTS_SCHEMA_VERSION = "d009.body-requirements.v1"
ENVIRONMENTAL_COST_SCHEMA_VERSION = "d009.environmental-cost.v1"
ORGANISM_EFFECT_SCHEMA_VERSION = "d009.organism-effect-contract.v1"
WORLD_EFFECT_SCHEMA_VERSION = "d009.world-effect-contract.v1"


class AffordanceOperation(str, Enum):
    PICK_UP = "PICK_UP"
    PLACE = "PLACE"
    PUSH = "PUSH"
    ACTIVATE = "ACTIVATE"
    DEACTIVATE = "DEACTIVATE"
    USE = "USE"


@dataclass(frozen=True)
class AffordancePreconditions:
    schema_version: str
    requires_free_location: bool = False
    requires_not_held: bool = False
    requires_held_by_body: bool = False
    requires_portable: bool = False
    requires_remaining_yield_min: float | None = None
    requires_station_available: bool | None = None
    requires_activatable_active: bool | None = None


@dataclass(frozen=True)
class BodyRequirements:
    schema_version: str
    required_capabilities: tuple[str, ...]
    maximum_held_mass_class: str | None = None


@dataclass(frozen=True)
class EnvironmentalCost:
    schema_version: str
    effort: float


@dataclass(frozen=True)
class OrganismEffectProposal:
    effect_kind: str
    magnitude: float


@dataclass(frozen=True)
class OrganismEffectContract:
    schema_version: str
    effects: tuple[OrganismEffectProposal, ...]


@dataclass(frozen=True)
class WorldEffectMutation:
    field: str
    delta: float | bool | str


@dataclass(frozen=True)
class WorldEffectContract:
    schema_version: str
    mutations: tuple[WorldEffectMutation, ...]


@dataclass(frozen=True)
class AffordanceDefinition:
    affordance_id: str
    target_object_kind: ObjectKind
    operation: AffordanceOperation
    required_capability: str
    preconditions: AffordancePreconditions
    body_requirements: BodyRequirements
    environmental_cost: EnvironmentalCost
    organism_effect_contract: OrganismEffectContract
    world_effect_contract: WorldEffectContract
    reversibility: str
    cooldown_ticks: int
    failure_modes: tuple[str, ...]
    definition_version: int
    definition_hash: str = ""


_DEFINITION_HASH_FIELDS = (
    "affordance_id",
    "target_object_kind",
    "operation",
    "required_capability",
    "preconditions",
    "body_requirements",
    "environmental_cost",
    "organism_effect_contract",
    "world_effect_contract",
    "reversibility",
    "cooldown_ticks",
    "failure_modes",
    "definition_version",
)


def definition_payload(defn: AffordanceDefinition) -> dict[str, Any]:
    serialized = canonical_serialize(defn)
    return {key: serialized[key] for key in _DEFINITION_HASH_FIELDS}


def definition_hash(defn: AffordanceDefinition) -> str:
    return sha256_hex(canon_json(definition_payload(defn)))


def with_definition_hash(defn: AffordanceDefinition) -> AffordanceDefinition:
    computed = definition_hash(defn)
    if defn.definition_hash and defn.definition_hash != computed:
        raise ValueError("affordance_definition_hash_mismatch")
    return AffordanceDefinition(**{**{f.name: getattr(defn, f.name) for f in fields(defn)}, "definition_hash": computed})


def _parse_preconditions(raw: dict[str, Any]) -> AffordancePreconditions:
    return AffordancePreconditions(
        schema_version=str(raw["schema_version"]),
        requires_free_location=bool(raw.get("requires_free_location", False)),
        requires_not_held=bool(raw.get("requires_not_held", False)),
        requires_held_by_body=bool(raw.get("requires_held_by_body", False)),
        requires_portable=bool(raw.get("requires_portable", False)),
        requires_remaining_yield_min=raw.get("requires_remaining_yield_min"),
        requires_station_available=raw.get("requires_station_available"),
        requires_activatable_active=raw.get("requires_activatable_active"),
    )


def _parse_definition(raw: dict[str, Any]) -> AffordanceDefinition:
    organism_effects = tuple(
        OrganismEffectProposal(effect_kind=str(item["effect_kind"]), magnitude=float(item["magnitude"]))
        for item in raw["organism_effect_contract"]["effects"]
    )
    world_mutations = tuple(
        WorldEffectMutation(field=str(item["field"]), delta=item["delta"])
        for item in raw["world_effect_contract"]["mutations"]
    )
    defn = AffordanceDefinition(
        affordance_id=str(raw["affordance_id"]),
        target_object_kind=ObjectKind(str(raw["target_object_kind"])),
        operation=AffordanceOperation(str(raw["operation"])),
        required_capability=str(raw["required_capability"]),
        preconditions=_parse_preconditions(raw["preconditions"]),
        body_requirements=BodyRequirements(
            schema_version=str(raw["body_requirements"]["schema_version"]),
            required_capabilities=tuple(str(c) for c in raw["body_requirements"]["required_capabilities"]),
            maximum_held_mass_class=raw["body_requirements"].get("maximum_held_mass_class"),
        ),
        environmental_cost=EnvironmentalCost(
            schema_version=str(raw["environmental_cost"]["schema_version"]),
            effort=float(raw["environmental_cost"]["effort"]),
        ),
        organism_effect_contract=OrganismEffectContract(
            schema_version=str(raw["organism_effect_contract"]["schema_version"]),
            effects=organism_effects,
        ),
        world_effect_contract=WorldEffectContract(
            schema_version=str(raw["world_effect_contract"]["schema_version"]),
            mutations=world_mutations,
        ),
        reversibility=str(raw["reversibility"]),
        cooldown_ticks=int(raw["cooldown_ticks"]),
        failure_modes=tuple(str(code) for code in raw.get("failure_modes", ())),
        definition_version=int(raw["definition_version"]),
        definition_hash=str(raw.get("definition_hash", "")),
    )
    return with_definition_hash(defn)


def load_affordance_definitions(raw_definitions: list[dict[str, Any]]) -> dict[str, AffordanceDefinition]:
    loaded = {item["affordance_id"]: _parse_definition(item) for item in raw_definitions}
    if len(loaded) != len(raw_definitions):
        raise ValueError("duplicate_affordance_id")
    return loaded


def load_affordance_definitions_file(path: str | Path) -> dict[str, AffordanceDefinition]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return load_affordance_definitions(list(data["definitions"]))


def default_affordance_definitions() -> dict[str, AffordanceDefinition]:
    repo_root = Path(__file__).resolve().parents[2]
    return load_affordance_definitions_file(repo_root / "experiments" / "d009" / "affordance-definitions.json")
